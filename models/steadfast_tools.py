import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SteadfastTool(models.TransientModel):
    _name = "steadfast.api.tool"
    _description = "Steadfast API Tool"

    carrier_id = fields.Many2one("delivery.carrier", required=True)
    operation = fields.Selection([
        ("ping", "Ping"), ("status_by_cid", "Status by Consignment ID"),
        ("status_with_return", "Status + Return Status by Consignment ID"),
        ("status_by_invoice", "Status by Invoice"), ("status_by_tracking", "Status by Tracking Code"),
        ("tracking_history", "Tracking History by Invoice"), ("return_list", "Return Requests"),
        ("return_get", "Return Request Detail"), ("balance", "Balance"),
        ("payments", "Payments"), ("payment", "Payment Detail"),
        ("police_stations", "Police Stations"), ("fraud", "Fraud Score"),
        ("custom_post_pickup", "Create Pickup Request"), ("custom_post_return", "Create Return Request"),
    ], required=True, default="ping")
    identifier = fields.Char(help="Consignment ID, invoice, tracking code, return ID, payment ID, or customer phone depending on the operation.")
    page = fields.Integer(default=1)
    payload_json = fields.Text()
    result_json = fields.Text(readonly=True)

    def action_execute(self):
        self.ensure_one()
        client = self.carrier_id._steadfast_client()
        op = self.operation
        if op == "ping": result = client.ping()
        elif op == "status_by_cid": result = client.status_by_cid(self.identifier)
        elif op == "status_with_return": result = client.status_with_return_by_cid(self.identifier)
        elif op == "status_by_invoice": result = client.status_by_invoice(self.identifier)
        elif op == "status_by_tracking": result = client.status_by_tracking_code(self.identifier)
        elif op == "tracking_history": result = client.tracking_history_by_invoice(self.identifier)
        elif op == "return_list": result = client.get_return_requests(self.page)
        elif op == "return_get": result = client.get_return_request(self.identifier)
        elif op == "balance": result = client.get_balance()
        elif op == "payments": result = client.get_payments(self.page)
        elif op == "payment": result = client.get_payment(self.identifier)
        elif op == "police_stations": result = client.get_police_stations()
        elif op == "fraud": result = client.fraud_score(self.identifier)
        elif op in {"custom_post_pickup", "custom_post_return"}:
            if not self.payload_json: raise UserError(_("Enter JSON payload."))
            try: payload = json.loads(self.payload_json)
            except ValueError as exc: raise UserError(_("Invalid JSON: %s") % exc) from exc
            result = client.create_pickup_request(payload) if op == "custom_post_pickup" else client.create_return_request(payload)
        else:
            raise UserError(_("Unsupported operation."))
        self.result_json = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "res_id": self.id, "target": "new"}
