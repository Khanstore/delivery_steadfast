# controllers/main.py
from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response
import json
import logging

_logger = logging.getLogger(__name__)

# Set this securely (or load from system parameters in production)


class DeliveryWebhookController(http.Controller):

    @http.route('/delivery/steadfast/callback', type='http', auth='public', methods=['POST'], csrf=False)
    def delivery_webhook_callback(self):
        try:
            # ✅ Check Authorization header
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return Response(json.dumps({"error": "Missing or invalid Authorization header"}), status=401, content_type='application/json')

            token = auth_header.split(' ')[1]
            if token != request.env['delivery.carrier'].sudo().search([('steadfast_auth_token', '!=', False)], limit=1).steadfast_auth_token:
                return Response(json.dumps({"error": "Unauthorized"}), status=403, content_type='application/json')

            # ✅ Read and parse JSON body
            raw_data = request.httprequest.data
            data = json.loads(raw_data.decode('utf-8'))
            _logger.info("Webhook received: %s", data)

            consignment_id = data.get('consignment_id')
            status = data.get('status')

            picking = request.env['stock.picking'].sudo().search([
                ('consignment_id', '=', str(consignment_id))
            ], limit=1)

            if picking:
                picking.tracking_status_changed_on=data.get('updated_at')
                picking.carrier_tracking_status=data.get("status")
                picking.message_post(body=f"📦 Webhook update received: Status = {status}")
                # Optional: store status
                # picking.steadfast_status = status
            else:
                _logger.warning("No picking found for consignment_id: %s", tracking_ref)

            return Response(json.dumps({"success": True}), status=200, content_type='application/json')

        except Exception as e:
            _logger.exception("Error in webhook callback")
            return Response(json.dumps({"success": False, "error": str(e)}), status=500, content_type='application/json')
