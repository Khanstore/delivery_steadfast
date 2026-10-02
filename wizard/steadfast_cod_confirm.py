from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SteadfastCodConfirmWizard(models.TransientModel):
    _name = "steadfast.cod.confirm.wizard"
    _description = "Confirm Steadfast COD Amount"

    picking_id = fields.Many2one("stock.picking", required=True, readonly=True)
    customer_name = fields.Char(related="picking_id.partner_id.name", readonly=True)
    order_amount = fields.Monetary(string="Order COD Amount", currency_field="currency_id", readonly=True)
    cod_amount = fields.Monetary(string="Steadfast COD Amount", currency_field="currency_id", required=True)
    currency_id = fields.Many2one(related="picking_id.company_id.currency_id", readonly=True)
    warning = fields.Char(readonly=True)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        picking_id = self.env.context.get("default_picking_id") or self.env.context.get("active_id")
        picking = self.env["stock.picking"].browse(picking_id).exists()
        if not picking:
            raise UserError(_("No delivery order was selected."))
        if picking.carrier_id.delivery_type != "steadfast":
            raise UserError(_("Select a Steadfast delivery method first."))
        default_amount = picking.steadfast_cod_amount or picking._steadfast_default_cod_amount(picking)
        vals.update({
            "picking_id": picking.id,
            "order_amount": picking._steadfast_default_cod_amount(picking),
            "cod_amount": default_amount,
            "warning": _("Review the amount to be collected from the customer, then click Confirm COD."),
        })
        return vals

    def action_confirm(self):
        self.ensure_one()
        picking = self.picking_id
        if not picking or picking.carrier_id.delivery_type != "steadfast":
            raise UserError(_("This delivery is no longer configured for Steadfast."))
        if self.cod_amount < 0:
            raise UserError(_("COD amount cannot be negative."))
        picking.write({
            "steadfast_cod_enabled": True,
            "steadfast_cod_amount": self.cod_amount,
            "steadfast_cod_confirmed": True,
        })
        picking.message_post(body=_("<b>Steadfast COD confirmed</b><br/>Amount to collect: <b>৳ %.2f</b>.") % self.cod_amount)
        # Confirmation and booking are one user action: once the amount is
        # confirmed, immediately send the delivery to Steadfast. This avoids
        # the old cycle where send_shipping raised the confirmation error
        # before a wizard could ever be shown.
        picking._steadfast_send_confirmed()
        return {"type": "ir.actions.act_window_close"}
