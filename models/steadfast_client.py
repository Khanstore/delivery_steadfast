import json
import logging
import time

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_URL = "https://portal.packzy.com/api/v1"

DELIVERY_STATUSES = {
    "pending", "in_review", "hold", "delivered_approval_pending",
    "partial_delivered_approval_pending", "cancelled_approval_pending",
    "unknown_approval_pending", "delivered", "partial_delivered", "cancelled",
    "exceptional", "unknown",
}

RETURN_STATUSES = {
    "partial_delivered_return_proccessing",
    "partial_delivered_return_rider_assigned",
    "partial_delivered_return_received",
    "cancelled_return_proccessing",
    "cancelled_return_rider_assigned",
    "cancelled_return_received",
}


class SteadfastAPIError(UserError):
    """Controlled exception for Steadfast API failures."""


class SteadfastClient:
    def __init__(self, carrier):
        self.carrier = carrier
        self.base_url = (carrier.steadfast_api_url or BASE_URL).rstrip("/")
        self.timeout = max(5, int(carrier.steadfast_timeout or 30))

    def _headers(self, authenticated=True):
        headers = {"Accept": "application/json"}
        if authenticated:
            if not self.carrier.steadfast_api_key or not self.carrier.steadfast_secret_key:
                raise SteadfastAPIError(_("Please configure the Steadfast API Key and Secret Key."))
            headers.update({
                "Api-Key": self.carrier.steadfast_api_key,
                "Secret-Key": self.carrier.steadfast_secret_key,
            })
        return headers

    def request(self, method, path, payload=None, authenticated=True, log=True):
        method = method.upper()
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._headers(authenticated=authenticated)
        if method == "POST":
            headers["Content-Type"] = "application/json"
        started = time.monotonic()
        request_payload = payload if payload is not None else None
        response = None
        try:
            response = requests.request(
                method,
                url,
                json=payload if method in {"POST", "PUT", "PATCH"} else None,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            self._log(method, path, request_payload, None, None, time.monotonic() - started, str(exc), log)
            raise SteadfastAPIError(_("Could not connect to Steadfast: %s") % exc) from exc

        duration = time.monotonic() - started
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        self._log(method, path, request_payload, body, response.status_code, duration, None, log)
        if response.status_code == 401:
            raise SteadfastAPIError(_("Steadfast authentication failed (401). Check the API Key and Secret Key; do not repeatedly retry invalid credentials."))
        if response.status_code == 403:
            raise SteadfastAPIError(_("Steadfast rejected the request (403). Check account status, permissions and KYC/ownership details."))
        if response.status_code == 422:
            errors = body.get("errors") if isinstance(body, dict) else None
            raise SteadfastAPIError(_("Steadfast validation failed (422): %s") % (json.dumps(errors or body, ensure_ascii=False)))
        if response.status_code == 429:
            raise SteadfastAPIError(_("Steadfast rate limit / temporary lockout (429). Please wait and try again."))
        if response.status_code >= 500:
            raise SteadfastAPIError(_("Steadfast server error (%s). Retrying the same invoice is safe according to the API documentation.") % response.status_code)
        if response.status_code >= 400:
            raise SteadfastAPIError(_("Steadfast API returned HTTP %s: %s") % (response.status_code, json.dumps(body, ensure_ascii=False)))
        return body

    def _log(self, method, endpoint, request_payload, response_payload, status_code, duration, error, enabled):
        if not enabled or not self.carrier.debug_logging:
            return
        try:
            self.carrier.env["steadfast.api.log"].sudo().create({
                "carrier_id": self.carrier.id,
                "method": method,
                "endpoint": endpoint,
                "request_json": self._safe_json(request_payload),
                "response_json": self._safe_json(response_payload),
                "http_status": status_code or 0,
                "duration": duration,
                "error_message": error or False,
            })
        except Exception:
            _logger.exception("Unable to create Steadfast API log")

    @staticmethod
    def _safe_json(value):
        if value is None:
            return False
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)

    def ping(self):
        return self.request("GET", "/ping", authenticated=False)

    def create_order(self, payload):
        return self.request("POST", "/create_order", payload)

    def create_bulk_order(self, payload, extended=False):
        endpoint = "/create_order/bulk-order/extended" if extended else "/create_order/bulk-order"
        return self.request("POST", endpoint, payload)

    def status_by_cid(self, consignment_id):
        return self.request("GET", f"/status_by_cid/{consignment_id}")

    def status_with_return_by_cid(self, consignment_id):
        return self.request("GET", f"/status_with_return_status_by_cid/{consignment_id}")

    def status_by_invoice(self, invoice):
        return self.request("GET", f"/status_by_invoice/{invoice}")

    def status_by_tracking_code(self, tracking_code):
        return self.request("GET", f"/status_by_trackingcode/{tracking_code}")

    def tracking_history_by_invoice(self, invoice):
        return self.request("GET", f"/trackings_by_invoice/{invoice}")

    def create_pickup_request(self, payload):
        return self.request("POST", "/create_pickup_request", payload)

    def create_return_request(self, payload):
        return self.request("POST", "/create_return_request", payload)

    def get_return_requests(self, page=1):
        endpoint = "/get_return_requests"
        if page:
            endpoint += f"?page={int(page)}"
        return self.request("GET", endpoint)

    def get_return_request(self, request_id):
        return self.request("GET", f"/get_return_request/{request_id}")

    def get_balance(self):
        return self.request("GET", "/get_balance")

    def get_payments(self, page=1):
        endpoint = "/payments"
        if page:
            endpoint += f"?page={int(page)}"
        return self.request("GET", endpoint)

    def get_payment(self, payment_id):
        return self.request("GET", f"/payments/{payment_id}")

    def get_police_stations(self):
        return self.request("GET", "/police_stations")

    def fraud_score(self, phone):
        return self.request("GET", f"/fraud_check/score/{phone}")
