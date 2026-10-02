import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SteadfastWebhookController(http.Controller):
    @staticmethod
    def _verify_signature(carrier, raw_body):
        """Verify Steadfast's optional bearer token and HMAC signature."""
        token = carrier.steadfast_webhook_token
        if not token:
            # Token is optional in Steadfast's webhook contract. If no token is
            # configured, the endpoint remains compatible with unsigned hooks.
            return True
        auth = request.httprequest.headers.get("Authorization", "")
        if not hmac.compare_digest(auth, "Bearer %s" % token):
            return False
        given = request.httprequest.headers.get("X-Signature", "")
        expected = hmac.new(token.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return bool(given) and hmac.compare_digest(given, expected)

    @http.route("/steadfast/webhook/<int:carrier_id>", type="http", auth="public", methods=["POST"], csrf=False)
    def steadfast_webhook(self, carrier_id, **kwargs):
        carrier = request.env["delivery.carrier"].sudo().browse(carrier_id).exists()
        if not carrier or carrier.delivery_type != "steadfast" or not carrier.steadfast_webhook_enabled:
            return request.make_json_response({"ok": False, "error": "Webhook disabled or carrier not found"}, status=404)

        raw = request.httprequest.get_data() or b""
        if not self._verify_signature(carrier, raw):
            return request.make_json_response({"ok": False, "error": "Invalid webhook signature"}, status=401)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, ValueError):
            return request.make_json_response({"ok": False, "error": "Invalid JSON"}, status=400)
        if not isinstance(payload, dict):
            return request.make_json_response({"ok": False, "error": "Webhook payload must be an object"}, status=400)

        event_type = payload.get("notification_type") or payload.get("event") or "unknown"
        idem = request.httprequest.headers.get("Idempotency-Key") or payload.get("idempotency_key")
        event_model = request.env["steadfast.webhook.event"].sudo()
        if idem:
            existing_event = event_model.search([("carrier_id", "=", carrier.id), ("idempotency_key", "=", idem)], limit=1)
            if existing_event:
                return request.make_json_response({"ok": True, "duplicate": True})

        event = event_model.create({
            "carrier_id": carrier.id,
            "notification_type": event_type,
            "idempotency_key": idem or False,
            "payload_json": json.dumps(payload, ensure_ascii=False, indent=2),
        })

        try:
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            candidates = [
                payload.get("consignment_id"), payload.get("tracking_code"), payload.get("invoice"),
                data.get("consignment_id"), data.get("tracking_code"), data.get("invoice"),
            ]
            shipment_model = request.env["steadfast.shipment"].sudo()
            shipment = shipment_model.browse()
            for value in filter(None, candidates):
                value = str(value)
                shipment = shipment_model.search([("consignment_id", "=", value)], limit=1)
                if not shipment:
                    shipment = shipment_model.search([("tracking_code", "=", value)], limit=1)
                if not shipment:
                    shipment = shipment_model.search([("invoice", "=", value)], limit=1)
                if shipment:
                    break

            if shipment and event_type in {"delivery_status", "tracking_update", "consignment_update", "return_request", "cancel_request"}:
                shipment._apply_status_response(payload, source="webhook")

            # A payment_request webhook may contain only a payment ID. Fetch the
            # authoritative payment record, then reflect it in the configured journal.
            if event_type == "payment_request":
                payment_id = payload.get("payment_id") or payload.get("id") or data.get("payment_id") or data.get("id")
                if payment_id:
                    payment_model = request.env["steadfast.payment"].sudo()
                    payment = payment_model.search([("carrier_id", "=", carrier.id), ("payment_id", "=", str(payment_id))], limit=1)
                    if not payment:
                        payment = payment_model.create({
                            "name": str(payment_id), "carrier_id": carrier.id, "payment_id": str(payment_id),
                            "response_json": json.dumps(payload, ensure_ascii=False, indent=2),
                        })
                    payment.action_refresh()
                    payment.action_create_journal_entry()

            event.write({"processed": True, "processing_error": False})
        except Exception as exc:
            _logger.exception("Steadfast webhook processing failed for event %s", event.id)
            event.write({"processing_error": str(exc)})
            # A 2xx response tells Steadfast the webhook was received. The event
            # is retained in Odoo for investigation/reprocessing instead of
            # forcing a retry loop for a local configuration error.

        return request.make_json_response({"ok": True})
