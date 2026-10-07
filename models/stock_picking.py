from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    steadfast_shipment_count = fields.Integer(compute="_compute_steadfast_shipment_count")
    steadfast_cod_enabled = fields.Boolean(string="Steadfast COD", default=True)
    steadfast_order_cod_amount = fields.Float(
        string="Order COD Amount",
        compute="_compute_steadfast_order_cod_amount",
        digits="Product Price",
        readonly=True,
    )
    steadfast_cod_amount = fields.Float(string="COD Amount to Collect", digits="Product Price")
    steadfast_cod_confirmed = fields.Boolean(string="COD Amount Confirmed", copy=False)
    steadfast_tracking_link = fields.Char(string="Steadfast Tracking Link", readonly=True, copy=False)
    steadfast_consignment_id = fields.Char(string="Steadfast Consignment ID", readonly=True, copy=False)
    steadfast_tracking_code = fields.Char(string="Steadfast Tracking Code", readonly=True, copy=False)
    steadfast_parcel_status = fields.Char(string="Steadfast Parcel Status", readonly=True, copy=False, tracking=True)
    steadfast_tracking_message = fields.Text(string="Steadfast Tracking Message", readonly=True, copy=False)
    steadfast_status_updated_at = fields.Datetime(string="Steadfast Status Updated", readonly=True, copy=False)
    steadfast_status_terminal = fields.Boolean(string="Steadfast Delivery Completed", readonly=True, copy=False)
    # Backward-compatible generic carrier status field used by older inherited
    # delivery-order views. For Steadfast it mirrors the parcel status. Keep it
    # non-stored so it does not introduce a migration column into existing DBs.
    carrier_tracking_status = fields.Char(
        string="Carrier Tracking Status",
        compute="_compute_carrier_tracking_status",
        readonly=True,
    )
    # Compatibility field for delivery-order views from earlier/custom
    # delivery integrations. Some existing databases still contain inherited
    # stock.picking views that reference carrier_tracking_time. Odoo 18 does
    # not provide that field by default, so keep a lightweight computed field
    # here rather than requiring a database migration.
    carrier_tracking_time = fields.Datetime(
        string="Carrier Tracking Time",
        compute="_compute_carrier_tracking_time",
        readonly=True,
    )
    # Compatibility field used by older delivery-order tracking views.
    # Keep it non-stored so existing databases do not need a column migration.
    tracking_status_changed_on = fields.Datetime(
        string="Tracking Status Changed On",
        related="steadfast_status_updated_at",
        readonly=True,
        store=False,
    )
    steadfast_is_carrier = fields.Boolean(string="Uses Steadfast", compute="_compute_steadfast_is_carrier", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            if (picking.carrier_id and picking.carrier_id.delivery_type == "steadfast"
                    and not picking.steadfast_cod_amount):
                picking.steadfast_cod_amount = picking._steadfast_default_cod_amount(picking)
        return pickings

    @api.depends("steadfast_parcel_status", "carrier_id", "carrier_id.delivery_type")
    def _compute_carrier_tracking_status(self):
        for picking in self:
            if picking.carrier_id and picking.carrier_id.delivery_type == "steadfast":
                picking.carrier_tracking_status = picking.steadfast_parcel_status or False
            else:
                picking.carrier_tracking_status = False

    @api.depends("steadfast_status_updated_at", "carrier_id", "carrier_id.delivery_type")
    def _compute_carrier_tracking_time(self):
        for picking in self:
            if picking.carrier_id and picking.carrier_id.delivery_type == "steadfast":
                picking.carrier_tracking_time = picking.steadfast_status_updated_at or False
            else:
                picking.carrier_tracking_time = False

    @api.depends("carrier_id", "carrier_id.delivery_type")
    def _compute_steadfast_is_carrier(self):
        for picking in self:
            picking.steadfast_is_carrier = bool(picking.carrier_id and picking.carrier_id.delivery_type == "steadfast")
    steadfast_pickup_location_id = fields.Many2one(
        "steadfast.pickup.location", string="Pickup From", copy=False,
        domain="[(\'carrier_id\', \'=\', carrier_id), (\'active\', \'=\', True)]",
    )
    steadfast_route = fields.Selection([
        ("inside_dhaka", "Inside Dhaka City"),
        ("dhaka_suburban", "Dhaka City → Dhaka Sub-urban"),
        ("dhaka_outside", "Dhaka City → Other City / District"),
        ("suburban_outside", "Dhaka Sub-urban → Other City"),
        ("outside_same_city", "Within Same City (Outside Dhaka)"),
    ], string="Steadfast Route", default="inside_dhaka")
    steadfast_weight = fields.Float(string="Steadfast Weight (kg)", digits=(16, 3))
    steadfast_base_charge = fields.Float(string="Base Delivery Charge")
    steadfast_weight_charge = fields.Float(string="Weight Surcharge")
    steadfast_cod_fee = fields.Float(string="COD / Risk Fee")
    steadfast_delivery_charge = fields.Float(string="Calculated Steadfast Charge")

    def _compute_steadfast_shipment_count(self):
        grouped = self.env["steadfast.shipment"].read_group([("picking_id", "in", self.ids)], ["picking_id"], ["picking_id"])
        counts = {item["picking_id"][0]: item["picking_id_count"] for item in grouped if item.get("picking_id")}
        for picking in self:
            picking.steadfast_shipment_count = counts.get(picking.id, 0)

    @api.depends("sale_id", "sale_id.amount_total", "sale_id.order_line.price_total", "sale_id.order_line.is_delivery")
    def _compute_steadfast_order_cod_amount(self):
        for picking in self:
            picking.steadfast_order_cod_amount = self._steadfast_default_cod_amount(picking)

    @staticmethod
    def _steadfast_default_cod_amount(picking):
        carrier = picking.carrier_id
        if not picking.sale_id or not carrier or carrier.delivery_type != "steadfast":
            return 0.0
        order = picking.sale_id
        # COD is the full amount the customer is expected to pay on delivery.
        # Odoo's sale order amount_total already includes the delivery line
        # (and its taxes) when a delivery charge is part of the order.
        return max(0.0, order.amount_total)

    def _steadfast_calculate_weight(self):
        self.ensure_one()
        weight = 0.0
        for move in self.move_ids.filtered(lambda m: m.state != "cancel"):
            qty = move.quantity or move.product_uom_qty
            weight += (move.product_id.weight or 0.0) * qty
        return weight or 0.5

    @api.onchange("steadfast_cod_amount")
    def _onchange_steadfast_cod_amount(self):
        for picking in self:
            if picking.steadfast_is_carrier and picking.steadfast_cod_confirmed:
                picking.steadfast_cod_confirmed = False

    @api.onchange("carrier_id")
    def _onchange_steadfast_carrier(self):
        for picking in self:
            carrier = picking.carrier_id
            if carrier and carrier.delivery_type == "steadfast":
                picking.steadfast_pickup_location_id = carrier.steadfast_default_pickup_location_id
                picking.steadfast_route = carrier.steadfast_default_route or "inside_dhaka"
                if not picking.steadfast_cod_amount:
                    picking.steadfast_cod_amount = picking._steadfast_default_cod_amount(picking)

    def action_steadfast_calculate_price(self):
        self.ensure_one()
        if self.carrier_id.delivery_type != "steadfast":
            raise UserError(_("Select a Steadfast delivery method first."))
        if not self.steadfast_cod_amount:
            self.steadfast_cod_amount = self._steadfast_default_cod_amount(self)
        self.steadfast_weight = self._steadfast_calculate_weight()
        return {
            "type": "ir.actions.act_window",
            "name": _("Steadfast Price Calculator"),
            "res_model": "steadfast.pricing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_carrier_id": self.carrier_id.id,
                "default_picking_id": self.id,
                "default_route": self.steadfast_route,
                "default_weight": self.steadfast_weight,
                "default_cod_amount": self.steadfast_cod_amount if self.steadfast_cod_enabled else 0.0,
            },
        }

    def action_steadfast_set_cod_amount(self):
        for picking in self:
            if picking.carrier_id.delivery_type != "steadfast":
                continue
            picking.write({"steadfast_cod_enabled": True, "steadfast_cod_amount": self._steadfast_default_cod_amount(picking), "steadfast_cod_confirmed": False})
        return True

    def button_validate(self):
        """Validate the delivery and automatically book Steadfast afterwards.

        The standard Odoo validation may return an Immediate Transfer or
        Backorder wizard action before the picking actually reaches ``done``.
        We therefore call the Steadfast booking only after ``super()`` has
        completed and the picking state is really ``done``.

        This keeps the existing manual Send-to-Steadfast flow intact while
        making the Delivery Order Validate button the automatic booking point
        for carriers configured with ``Auto-create Shipment on Validation``.
        """
        result = super().button_validate()

        # Do not book while Odoo has opened a validation wizard. In particular,
        # a backorder wizard can be returned after the current picking has
        # already moved to ``done``; booking at that point would send the parcel
        # before the user has decided how to handle the backorder. The wizard
        # will call validation again after the user's choice.
        if isinstance(result, dict) and result.get("res_model") in {
            "stock.immediate.transfer",
            "stock.backorder.confirmation",
        }:
            return result

        completed = self.filtered(
            lambda p: p.state == "done"
            and p.carrier_id
            and p.carrier_id.delivery_type == "steadfast"
            and p.carrier_id.steadfast_auto_book
        )

        for picking in completed:
            # Validation itself is the user's explicit send instruction, so an
            # unconfirmed COD amount is accepted here using the current amount
            # on the delivery order. This avoids reopening the COD wizard after
            # the Validate button has already completed the stock operation.
            if picking.steadfast_cod_enabled and not picking.steadfast_cod_confirmed:
                amount = picking.steadfast_cod_amount
                if not amount:
                    amount = picking._steadfast_default_cod_amount(picking)
                    picking.steadfast_cod_amount = amount
                picking.steadfast_cod_confirmed = True
                picking.message_post(
                    body=_(
                        "<b>Steadfast COD automatically confirmed on validation</b><br/>"
                        "Amount to collect: <b>৳ %.2f</b>."
                    ) % amount
                )

            # The carrier method already prevents duplicate consignments when a
            # shipment exists for this picking. It also creates/posts the COD
            # journal entry using the confirmed COD amount.
            picking._steadfast_send_confirmed()

        return result

    def send_to_shipper(self):
        """Intercept Odoo's standard Send to Shipper action for Steadfast.

        Odoo normally calls the carrier's send_shipping() directly. For
        Steadfast we must open the COD confirmation wizard first, otherwise
        the carrier-level safety check raises before the user can confirm.
        """
        self.ensure_one()
        if self.carrier_id and self.carrier_id.delivery_type == "steadfast":
            return self.action_steadfast_send_to_shipper()
        return super().send_to_shipper()

    def action_steadfast_send_to_shipper(self):
        """Manual Steadfast send flow: confirm COD first, then call the carrier API."""
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != "steadfast":
            raise UserError(_("Select a Steadfast delivery method first."))
        if self.steadfast_cod_enabled and not self.steadfast_cod_confirmed:
            return self.action_steadfast_confirm_cod_wizard()
        return self._steadfast_send_confirmed()

    def _steadfast_send_confirmed(self):
        self.ensure_one()
        if self.carrier_id.delivery_type != "steadfast":
            raise UserError(_("Select a Steadfast delivery method first."))
        result = self.carrier_id.send_shipping(self)
        if not result:
            raise UserError(_("Steadfast did not return a shipment result."))
        return result

    def action_steadfast_confirm_cod_wizard(self):
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != "steadfast":
            raise UserError(_("Select a Steadfast delivery method first."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirm Steadfast COD"),
            "res_model": "steadfast.cod.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_picking_id": self.id,
            },
        }

    def action_steadfast_confirm_cod(self):
        for picking in self:
            if not picking.carrier_id or picking.carrier_id.delivery_type != "steadfast":
                continue
            if not picking.steadfast_cod_enabled:
                raise UserError(_("Enable Steadfast COD first if this delivery requires cash collection."))
            if picking.steadfast_cod_amount < 0:
                raise UserError(_("COD amount cannot be negative."))
            if not picking.steadfast_cod_amount:
                amount = self._steadfast_default_cod_amount(picking)
                if amount:
                    picking.steadfast_cod_amount = amount
            picking.steadfast_cod_confirmed = True
            picking.message_post(body=_(
                "<b>Steadfast COD confirmed</b><br/>Amount to collect: <b>৳ %.2f</b>."
            ) % picking.steadfast_cod_amount)
        return True


    def action_steadfast_refresh_status(self):
        """Refresh the linked Steadfast shipment and mirror its status on the delivery order."""
        for picking in self:
            shipment = self.env["steadfast.shipment"].search([("picking_id", "=", picking.id)], limit=1)
            if shipment:
                shipment.action_refresh_status()
        return True

    def action_steadfast_refresh_status_if_needed(self):
        """Called by the backend form when a Steadfast delivery is opened.

        Webhooks are the primary mechanism; this is a lightweight fallback for
        deliveries that are not terminal or whose webhook has not arrived yet.
        """
        for picking in self:
            if picking.carrier_id.delivery_type != "steadfast":
                continue
            shipment = self.env["steadfast.shipment"].search([("picking_id", "=", picking.id)], limit=1)
            if shipment and not shipment.is_terminal: 
                shipment.action_refresh_status()
        return True

    def action_open_steadfast_tracking(self):
        self.ensure_one()
        shipment = self.env["steadfast.shipment"].search([("picking_id", "=", self.id)], limit=1)
        url = (shipment.tracking_link if shipment else False) or self.steadfast_tracking_link
        if not url:
            raise UserError(_("No Steadfast tracking link is available yet."))
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    def action_open_steadfast_shipment(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Steadfast Shipment", "res_model": "steadfast.shipment", "view_mode": "list,form", "domain": [("picking_id", "=", self.id)]}
