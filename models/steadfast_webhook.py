from odoo import fields, models


class SteadfastWebhookEvent(models.Model):
    _name = "steadfast.webhook.event"
    _description = "Steadfast Webhook Event"
    _order = "create_date desc, id desc"

    carrier_id = fields.Many2one("delivery.carrier", ondelete="set null", index=True)
    notification_type = fields.Char(index=True)
    idempotency_key = fields.Char(index=True)
    processed = fields.Boolean(default=False)
    processing_error = fields.Text()
    payload_json = fields.Text()
