from odoo import fields, models


class SteadfastAPILog(models.Model):
    _name = "steadfast.api.log"
    _description = "Steadfast API Log"
    _order = "create_date desc, id desc"

    carrier_id = fields.Many2one("delivery.carrier", ondelete="set null", index=True)
    method = fields.Selection([("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("PATCH", "PATCH")], required=True)
    endpoint = fields.Char(required=True)
    request_json = fields.Text()
    response_json = fields.Text()
    http_status = fields.Integer()
    duration = fields.Float(string="Duration (seconds)")
    error_message = fields.Text()
