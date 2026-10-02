import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SteadfastPickupLocation(models.Model):
    _name = "steadfast.pickup.location"
    _description = "Steadfast Pickup Location"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    carrier_id = fields.Many2one("delivery.carrier", required=True, ondelete="cascade")
    sender_name = fields.Char(required=True)
    sender_phone = fields.Char(required=True)
    sender_email = fields.Char()
    address = fields.Text(required=True)
    city = fields.Char()
    state = fields.Char()
    zip = fields.Char()
    country = fields.Char(default="Bangladesh")



class SteadfastPickupRequest(models.Model):
    _name = "steadfast.pickup.request"
    _description = "Steadfast Pickup Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="New", readonly=True, copy=False)
    carrier_id = fields.Many2one("delivery.carrier", required=True, ondelete="cascade")
    pickup_location_id = fields.Many2one("steadfast.pickup.location", string="Pickup From")
    sender_name = fields.Char()
    sender_phone = fields.Char()
    sender_email = fields.Char()
    pickup_address = fields.Text()
    pickup_city = fields.Char()
    state = fields.Char(default="draft", tracking=True)
    payload_json = fields.Text(help="Exact JSON payload to send to Steadfast.")
    response_json = fields.Text(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") in (False, "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("steadfast.pickup.request") or "New"
        return super().create(vals_list)

    @api.onchange("pickup_location_id")
    def _onchange_pickup_location(self):
        for rec in self:
            loc = rec.pickup_location_id
            if loc:
                rec.sender_name = loc.sender_name
                rec.sender_phone = loc.sender_phone
                rec.sender_email = loc.sender_email
                rec.pickup_address = loc.address
                rec.pickup_city = loc.city

    def action_generate_payload(self):
        for rec in self:
            if not rec.pickup_location_id and not rec.pickup_address:
                raise UserError(_("Select a pickup location or enter a pickup address."))
            rec.payload_json = json.dumps({
                "pickup_name": rec.sender_name or "",
                "pickup_phone": rec.sender_phone or "",
                "pickup_email": rec.sender_email or "",
                "pickup_address": rec.pickup_address or "",
                "pickup_city": rec.pickup_city or "",
            }, ensure_ascii=False, indent=2)
        return True

    def action_send(self):
        for rec in self:
            if not rec.payload_json:
                rec.action_generate_payload()
            try:
                payload = json.loads(rec.payload_json)
            except ValueError as exc:
                raise UserError(_("Invalid JSON: %s") % exc) from exc
            response = rec.carrier_id._steadfast_client().create_pickup_request(payload)
            rec.response_json = json.dumps(response, ensure_ascii=False, indent=2)
            data = response.get("data", response) if isinstance(response, dict) else {}
            if isinstance(data, dict):
                rec.state = data.get("status") or "submitted"
            else:
                rec.state = "submitted"
        return True
