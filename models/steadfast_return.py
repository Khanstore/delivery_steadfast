import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SteadfastReturnRequest(models.Model):
    _name = "steadfast.return.request"
    _description = "Steadfast Return Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="New", readonly=True, copy=False)
    carrier_id = fields.Many2one("delivery.carrier", required=True, ondelete="cascade")
    shipment_id = fields.Many2one("steadfast.shipment", ondelete="set null")
    request_id = fields.Char(index=True)
    state = fields.Char(default="unknown", tracking=True)
    payload_json = fields.Text(help="Exact JSON payload to send to Steadfast. The supplied API document does not specify the request schema for this endpoint.")
    response_json = fields.Text(readonly=True)
    page = fields.Integer(default=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") in (False, "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("steadfast.return.request") or "New"
        return super().create(vals_list)

    def action_send(self):
        for rec in self:
            if not rec.payload_json:
                raise UserError(_("Enter the Steadfast return request JSON payload."))
            try:
                payload = json.loads(rec.payload_json)
            except ValueError as exc:
                raise UserError(_("Invalid JSON: %s") % exc) from exc
            response = rec.carrier_id._steadfast_client().create_return_request(payload)
            rec.response_json = json.dumps(response, ensure_ascii=False, indent=2)
            data = response.get("data", response) if isinstance(response, dict) else {}
            if isinstance(data, dict):
                rec.request_id = str(data.get("id") or data.get("return_request_id") or rec.request_id or "") or False
                rec.state = data.get("status") or rec.state
        return True

    def action_refresh(self):
        for rec in self:
            if not rec.request_id:
                raise UserError(_("No return request ID is stored."))
            response = rec.carrier_id._steadfast_client().get_return_request(rec.request_id)
            rec.response_json = json.dumps(response, ensure_ascii=False, indent=2)
        return True

    def action_load_list(self):
        self.ensure_one()
        response = self.carrier_id._steadfast_client().get_return_requests(self.page)
        self.response_json = json.dumps(response, ensure_ascii=False, indent=2)
        return True
