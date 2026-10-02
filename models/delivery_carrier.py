import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .steadfast_client import BASE_URL, SteadfastClient, SteadfastAPIError


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("steadfast", "Steadfast Courier")],
        ondelete={"steadfast": "set default"},
    )
    # Kept intentionally named `related_journal` for compatibility with the
    # user's earlier Steadfast connector and any existing inherited views.
    # It is the dedicated account journal used to identify/track Steadfast
    # COD-related accounting transactions.
    related_journal = fields.Many2one(
        "account.journal",
        string="Related Journal",
        company_dependent=True,
        domain="[(\'company_id\', \'=\', company_id), (\'type\', \'in\', [\'bank\', \'cash\'])]",
        help="Dedicated cash/bank journal used to track Steadfast COD transactions. "
             "This preserves compatibility with the earlier Steadfast connector.",
    )
    steadfast_cod_journal = fields.Many2one(
        "account.journal",
        related="related_journal",
        string="Steadfast COD Journal",
        readonly=False,
        domain="[(\'company_id\', \'=\', company_id), (\'type\', \'in\', [\'bank\', \'cash\'])]",
        help="Alias for the dedicated Steadfast COD journal.",
    )

    steadfast_api_url = fields.Char(
        string="API Base URL", default=BASE_URL,
        help="Steadfast API base URL. The standard value is https://portal.packzy.com/api/v1.",
    )
    steadfast_api_key = fields.Char(string="API Key", copy=False)
    steadfast_secret_key = fields.Char(string="Secret Key", copy=False)
    steadfast_timeout = fields.Integer(string="API Timeout (seconds)", default=30)
    steadfast_auto_sync = fields.Boolean(string="Automatic Status Sync", default=True)
    steadfast_webhook_enabled = fields.Boolean(string="Webhook Enabled", default=True)
    steadfast_webhook_token = fields.Char(
        string="Webhook Auth Token", copy=False, password=True,
        help="Optional token supplied by Steadfast. When configured, the webhook verifies Authorization: Bearer <token> and the X-Signature HMAC-SHA256 header.",
    )
    steadfast_webhook_path = fields.Char(
        string="Webhook Endpoint Path", compute="_compute_steadfast_webhook_path",
        readonly=True, help="Configure this path in Steadfast together with your public HTTPS domain."
    )

    def _compute_steadfast_webhook_path(self):
        for carrier in self:
            carrier.steadfast_webhook_path = "/steadfast/webhook/%s" % carrier.id if carrier.id else False
    steadfast_auto_book = fields.Boolean(string="Auto-create Shipment on Validation", default=True)
    steadfast_cod_from_order = fields.Boolean(
        string="Use Order Total as COD", default=True,
        help="When enabled, COD is calculated from the sale order total excluding the delivery line.",
    )
    steadfast_tracking_base_url = fields.Char(
        string="Tracking Page URL",
        help="Optional customer tracking page URL. Use <tracking_code> as placeholder.",
    )
    steadfast_last_balance = fields.Float(string="Last Known Balance", readonly=True)
    steadfast_last_balance_sync = fields.Datetime(string="Balance Last Updated", readonly=True)
    steadfast_inside_dhaka_charge = fields.Float(string="Inside Dhaka Base", default=60.0)
    steadfast_dhaka_suburban_charge = fields.Float(string="Dhaka → Sub-urban Base", default=105.0)
    steadfast_dhaka_outside_charge = fields.Float(string="Dhaka → Other District Base", default=115.0)
    steadfast_suburban_outside_charge = fields.Float(string="Sub-urban → Other District Base", default=135.0)
    steadfast_outside_same_city_charge = fields.Float(string="Outside Dhaka Same City Base", default=60.0)
    steadfast_base_weight_kg = fields.Float(string="Included Weight (kg)", default=1.0)
    steadfast_extra_weight_step_kg = fields.Float(string="Extra Weight Step (kg)", default=1.0)
    steadfast_extra_weight_charge = fields.Float(string="Charge per Extra Weight Step", default=20.0)
    steadfast_cod_fee_percent = fields.Float(string="COD / Risk Fee (%)", default=1.0)
    steadfast_default_route = fields.Selection([
        ("inside_dhaka", "Inside Dhaka City"),
        ("dhaka_suburban", "Dhaka City → Dhaka Sub-urban"),
        ("dhaka_outside", "Dhaka City → Other City / District"),
        ("suburban_outside", "Dhaka Sub-urban → Other City"),
        ("outside_same_city", "Within Same City (Outside Dhaka)"),
    ], string="Default Pricing Route", default="inside_dhaka")
    steadfast_default_pickup_location_id = fields.Many2one(
        "steadfast.pickup.location", string="Default Pickup Location",
        domain="[(\'carrier_id\', \'=\', id), (\'active\', \'=\', True)]",
    )
    steadfast_cod_receivable_account = fields.Many2one(
        "account.account", string="COD Receivable Account", company_dependent=True,
        domain="[(\'deprecated\', \'=\', False)]",
        help="Asset account used to reclassify COD receivables from the customer to Steadfast until settlement.",
    )

    def _steadfast_base_charge(self, route):
        self.ensure_one()
        return {
            "inside_dhaka": self.steadfast_inside_dhaka_charge,
            "dhaka_suburban": self.steadfast_dhaka_suburban_charge,
            "dhaka_outside": self.steadfast_dhaka_outside_charge,
            "suburban_outside": self.steadfast_suburban_outside_charge,
            "outside_same_city": self.steadfast_outside_same_city_charge,
        }.get(route or "inside_dhaka", self.steadfast_inside_dhaka_charge)

    def _steadfast_weight_charge(self, weight):
        self.ensure_one()
        extra = max(0.0, (weight or 0.0) - (self.steadfast_base_weight_kg or 0.0))
        step = self.steadfast_extra_weight_step_kg or 1.0
        import math
        return math.ceil(extra / step) * self.steadfast_extra_weight_charge if extra > 0 else 0.0

    @api.constrains("steadfast_timeout")
    def _check_steadfast_timeout(self):
        for carrier in self:
            if carrier.delivery_type == "steadfast" and not 5 <= carrier.steadfast_timeout <= 300:
                raise ValidationError(_("Steadfast API timeout must be between 5 and 300 seconds."))

    def _steadfast_client(self):
        self.ensure_one()
        if self.delivery_type != "steadfast":
            raise UserError(_("This delivery method is not configured for Steadfast."))
        return SteadfastClient(self)

    def action_steadfast_test_connection(self):
        self.ensure_one()
        result = self._steadfast_client().ping()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Steadfast"), "message": _("Connection successful: %s") % json.dumps(result, ensure_ascii=False), "type": "success", "sticky": False},
        }

    def steadfast_rate_shipment(self, order):
        if self.delivery_type != "steadfast":
            return {"success": False, "price": 0.0, "error_message": _("Not a Steadfast carrier."), "warning_message": False}
        if not self._match_address(order.partner_shipping_id):
            return {"success": False, "price": 0.0, "error_message": _("Steadfast is not available for this destination."), "warning_message": False}
        route = self.steadfast_default_route or "inside_dhaka"
        weight = sum((line.product_id.weight or 0.0) * line.product_uom_qty for line in order.order_line if not line.is_delivery) or 0.5
        cod = max(0.0, order.amount_total - sum(line.price_total for line in order.order_line if line.is_delivery)) if self.steadfast_cod_from_order else 0.0
        price = self._steadfast_base_charge(route) + self._steadfast_weight_charge(weight) + (cod * self.steadfast_cod_fee_percent / 100.0 if cod else 0.0)
        return {"success": True, "price": price, "error_message": False, "warning_message": False}

    @staticmethod
    def _clean_text(value, max_len):
        value = (value or "").strip()
        value = re.sub(r"[{};<>$]", " ", value)
        return value[:max_len]

    def _steadfast_invoice(self, picking):
        # Steadfast accepts only letters, numbers, dashes and underscores.
        value = re.sub(r"[^A-Za-z0-9_-]+", "_", picking.name or "")
        value = re.sub(r"_+", "_", value).strip("_")
        return (value or "ODOO")[:100]

    def _steadfast_cod_amount(self, picking):
        if hasattr(picking, "steadfast_cod_amount") and picking.steadfast_cod_confirmed:
            return max(0.0, picking.steadfast_cod_amount)
        if not self.steadfast_cod_from_order or not picking.sale_id:
            return 0.0
        order = picking.sale_id
        delivery_total = sum(line.price_total for line in order.order_line if line.is_delivery)
        return max(0.0, order.amount_total - delivery_total)

    def _steadfast_product_note(self, picking):
        lines = []
        for move in picking.move_ids.filtered(lambda m: m.state != "cancel"):
            qty = move.quantity or move.product_uom_qty
            if not move.product_id or not qty:
                continue
            uom = move.product_uom.name or ""
            lines.append("%s x %s%s" % (move.product_id.display_name, qty, (" " + uom) if uom else ""))
        return "Products: " + "; ".join(lines) if lines else "Products: None"

    def _steadfast_order_payload(self, picking):
        partner = picking.partner_id
        address = ", ".join(filter(None, [partner.street, partner.street2, partner.city, partner.state_id.name, partner.zip, partner.country_id.name]))
        base_note = picking.sale_id.note if picking.sale_id else picking.note
        product_note = self._steadfast_product_note(picking)
        note = " | ".join(filter(None, [product_note, base_note]))
        return {
            "invoice": self._steadfast_invoice(picking),
            "recipient_name": self._clean_text(partner.name, 100),
            "recipient_phone": self._clean_text(partner.mobile or partner.phone, 40),
            "recipient_address": self._clean_text(address, 490),
            "cod_amount": self._steadfast_cod_amount(picking),
            "note": self._clean_text(note, 480),
        }

    def _steadfast_get_invoice(self, picking):
        """Return the customer invoice related to this delivery, if available."""
        invoices = self.env["account.move"]
        if picking.sale_id:
            invoices = picking.sale_id.invoice_ids.filtered(
                lambda inv: inv.move_type in ("out_invoice", "out_refund") and inv.state != "cancel"
            )
        if not invoices:
            # Fallback for manually created deliveries.
            invoices = self.env["account.move"].search([
                ("move_type", "=", "out_invoice"),
                ("partner_id", "=", picking.partner_id.id),
                ("state", "!=", "cancel"),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
            ], order="invoice_date desc, id desc", limit=1)
        return invoices[:1]

    def _steadfast_reconcile_cod_invoice(self, picking, move):
        """Transfer the invoice receivable to the Steadfast COD receivable account.

        The customer invoice is considered settled from the customer's side, while
        the amount remains outstanding in the dedicated Steadfast COD receivable
        account until Steadfast sends a settlement/payment.
        """
        invoice = self._steadfast_get_invoice(picking)
        if not invoice or invoice.state != "posted" or not move or move.state != "posted":
            return False
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and line.partner_id == picking.partner_id
            and not line.reconciled
        )
        reclass_lines = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and line.partner_id == picking.partner_id
            and line.credit > 0
            and not line.reconciled
        )
        if not receivable_lines or not reclass_lines:
            return False
        # Reconcile only the common amount; partial COD is supported.
        remaining = sum(reclass_lines.mapped("credit"))
        for line in receivable_lines.sorted("id"):
            if remaining <= 0:
                break
            available = line.debit - line.credit
            if available <= 0:
                continue
            remaining -= min(available, remaining)
        lines = (receivable_lines | reclass_lines).filtered(lambda line: not line.reconciled)
        if lines:
            lines.reconcile()
        return True

    def _steadfast_create_cod_move(self, picking, shipment, post=True):
        self.ensure_one()
        if not picking.steadfast_cod_enabled or not picking.steadfast_cod_amount:
            return False
        if shipment.cod_move_id:
            move = shipment.cod_move_id
            if post and move.state == "draft":
                move.action_post()
            self._steadfast_reconcile_cod_invoice(picking, move)
            return move
        journal = self.related_journal
        cod_account = self.steadfast_cod_receivable_account
        customer_account = picking.partner_id.property_account_receivable_id
        if not journal or not cod_account or not customer_account:
            return False
        amount = picking.steadfast_cod_amount
        move = self.env["account.move"].create({
            "move_type": "entry",
            "journal_id": journal.id,
            "date": fields.Date.context_today(self),
            "ref": _("Steadfast COD %s") % (shipment.invoice or picking.name),
            "line_ids": [
                (0, 0, {"name": _("Steadfast COD Receivable"), "account_id": cod_account.id, "partner_id": picking.partner_id.id, "debit": amount, "credit": 0.0}),
                (0, 0, {"name": _("Customer Receivable Reclassification"), "account_id": customer_account.id, "partner_id": picking.partner_id.id, "debit": 0.0, "credit": amount}),
            ],
        })
        if post:
            move.action_post()
        shipment.cod_move_id = move.id
        if move.state == "posted":
            self._steadfast_reconcile_cod_invoice(picking, move)
        return move

    def steadfast_send_shipping(self, pickings):
        results = []
        for picking in pickings:
            if picking.steadfast_cod_enabled and not picking.steadfast_cod_confirmed:
                raise UserError(_("Confirm the Steadfast COD amount before sending this delivery."))
            if not picking.steadfast_delivery_charge:
                weight = picking._steadfast_calculate_weight()
                cod = picking.steadfast_cod_amount if picking.steadfast_cod_enabled else 0.0
                base = self._steadfast_base_charge(picking.steadfast_route or self.steadfast_default_route)
                weight_charge = self._steadfast_weight_charge(weight)
                cod_fee = cod * self.steadfast_cod_fee_percent / 100.0 if cod else 0.0
                picking.write({"steadfast_weight": weight, "steadfast_base_charge": base, "steadfast_weight_charge": weight_charge, "steadfast_cod_fee": cod_fee, "steadfast_delivery_charge": base + weight_charge + cod_fee})
            existing = self.env["steadfast.shipment"].search([("picking_id", "=", picking.id)], limit=1)
            if existing and existing.consignment_id:
                results.append({"exact_price": picking.carrier_id.fixed_price, "tracking_number": existing.tracking_code or existing.consignment_id})
                continue
            payload = self._steadfast_order_payload(picking)
            try:
                response = self._steadfast_client().create_order(payload)
            except SteadfastAPIError:
                raise
            data = response.get("data", response) if isinstance(response, dict) else {}
            # Steadfast create_order returns the actual identifiers under
            # response["consignment"], e.g. {"status": 200, "consignment": {...}}.
            consignment = response.get("consignment") if isinstance(response, dict) else {}
            if not isinstance(consignment, dict):
                consignment = {}
            if not isinstance(data, dict):
                data = {}
            consignment_id = (consignment.get("consignment_id") or data.get("consignment_id")
                              or response.get("consignment_id"))
            tracking_code = (consignment.get("tracking_code") or data.get("tracking_code")
                             or response.get("tracking_code"))
            tracking_link = (consignment.get("tracking_link") or data.get("tracking_link")
                             or response.get("tracking_link"))
            invoice = (consignment.get("invoice") or data.get("invoice")
                       or response.get("invoice") or payload["invoice"])
            if not consignment_id and not tracking_code:
                raise UserError(_("Steadfast accepted the request but returned no consignment/tracking identifier. Response: %s") % json.dumps(response, ensure_ascii=False))
            shipment = existing or self.env["steadfast.shipment"].create({"carrier_id": self.id, "picking_id": picking.id, "sale_id": picking.sale_id.id})
            shipment.write({
                "invoice": invoice,
                "consignment_id": consignment_id or False,
                "tracking_code": tracking_code or False,
                "tracking_link": tracking_link or False,
                "cod_amount": picking.steadfast_cod_amount if picking.steadfast_cod_enabled else 0.0,
                "delivery_charge": picking.steadfast_delivery_charge or 0.0,
                "state": "in_review",
                "last_response": json.dumps(response, ensure_ascii=False, indent=2),
            })
            picking.write({
                "carrier_tracking_ref": tracking_code or consignment_id,
                "steadfast_tracking_link": tracking_link or False,
                "steadfast_consignment_id": str(consignment_id) if consignment_id else False,
                "steadfast_tracking_code": tracking_code or False,
                "steadfast_parcel_status": "in_review",
                "steadfast_tracking_message": False,
                "steadfast_status_updated_at": fields.Datetime.now(),
                "steadfast_status_terminal": False,
            })
            if picking.steadfast_cod_enabled and picking.steadfast_cod_confirmed:
                self._steadfast_create_cod_move(picking, shipment, post=True)
            results.append({"exact_price": picking.carrier_id.fixed_price, "tracking_number": tracking_code or consignment_id})
        return results

    def steadfast_get_tracking_link(self, picking):
        shipment = self.env["steadfast.shipment"].search([("picking_id", "=", picking.id)], limit=1)
        if shipment and shipment.tracking_link:
            return shipment.tracking_link
        code = (shipment.tracking_code if shipment else False) or picking.carrier_tracking_ref
        if not code:
            return False
        if self.steadfast_tracking_base_url:
            return self.steadfast_tracking_base_url.replace("<tracking_code>", code)
        return False

    def steadfast_cancel_shipment(self, pickings):
        # The supplied Steadfast documentation does not define a cancel endpoint.
        # We deliberately do not invent one. Use the return-request endpoint where appropriate.
        raise UserError(_("Steadfast's supplied API documentation does not provide a shipment-cancellation endpoint. Use the Return Request operation where applicable."))

    def action_steadfast_refresh_balance(self):
        for carrier in self.filtered(lambda c: c.delivery_type == "steadfast"):
            response = carrier._steadfast_client().get_balance()
            amount = 0.0
            if isinstance(response, dict):
                data = response.get("data", response)
                if isinstance(data, dict):
                    amount = data.get("balance") or data.get("current_balance") or 0.0
                elif isinstance(data, (int, float)):
                    amount = data
            carrier.write({"steadfast_last_balance": float(amount or 0.0), "steadfast_last_balance_sync": fields.Datetime.now()})
        return True

    @api.model
    def cron_steadfast_sync(self):
        carriers = self.search([("delivery_type", "=", "steadfast"), ("active", "=", True), ("steadfast_auto_sync", "=", True)])
        for carrier in carriers:
            shipments = self.env["steadfast.shipment"].search([("carrier_id", "=", carrier.id), ("state", "not in", ["delivered", "cancelled"])], limit=200)
            for shipment in shipments:
                try:
                    shipment.action_refresh_status()
                except Exception as exc:
                    shipment.message_post(body=_("Automatic Steadfast status sync failed: %s") % exc)
        return True
