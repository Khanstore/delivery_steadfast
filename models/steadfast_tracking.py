from odoo import fields, models


class SteadfastTrackingEvent(models.Model):
    _name = "steadfast.tracking.event"
    _description = "Steadfast Tracking Event"
    _order = "event_date desc, id desc"

    shipment_id = fields.Many2one("steadfast.shipment", required=True, ondelete="cascade", index=True)
    status = fields.Char(required=True)
    event_date = fields.Datetime()
    description = fields.Text()
    raw_json = fields.Text()
    event_hash = fields.Text(index=True)
