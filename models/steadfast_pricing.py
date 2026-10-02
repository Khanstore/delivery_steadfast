from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SteadfastPricingWizard(models.TransientModel):
    _name = "steadfast.pricing.wizard"
    _description = "Steadfast Price Calculator"

    carrier_id = fields.Many2one("delivery.carrier", required=True)
    route = fields.Selection(related="picking_id.steadfast_route", readonly=False)
    picking_id = fields.Many2one("stock.picking", required=True)
    weight = fields.Float(string="Weight (kg)", digits=(16, 3))
    cod_amount = fields.Float(string="COD Amount")
    base_charge = fields.Float(compute="_compute_price", store=False)
    weight_charge = fields.Float(compute="_compute_price", store=False)
    cod_fee = fields.Float(compute="_compute_price", store=False)
    total_charge = fields.Float(compute="_compute_price", store=False)

    @api.depends("route", "weight", "cod_amount", "carrier_id.steadfast_cod_fee_percent")
    def _compute_price(self):
        for rec in self:
            rec.base_charge = rec.carrier_id._steadfast_base_charge(rec.route)
            rec.weight_charge = rec.carrier_id._steadfast_weight_charge(rec.weight)
            rec.cod_fee = rec.cod_amount * (rec.carrier_id.steadfast_cod_fee_percent / 100.0) if rec.cod_amount else 0.0
            rec.total_charge = rec.base_charge + rec.weight_charge + rec.cod_fee

    def action_apply(self):
        for rec in self:
            if not rec.picking_id:
                raise UserError(_("No delivery order was selected."))
            rec.picking_id.write({
                "steadfast_route": rec.route,
                "steadfast_weight": rec.weight,
                "steadfast_base_charge": rec.base_charge,
                "steadfast_weight_charge": rec.weight_charge,
                "steadfast_cod_fee": rec.cod_fee,
                "steadfast_delivery_charge": rec.total_charge,
            })
        return {"type": "ir.actions.act_window_close"}
