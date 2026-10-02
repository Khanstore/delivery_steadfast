import json
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .steadfast_client import SteadfastAPIError


class SteadfastShipment(models.Model):
    _name = "steadfast.shipment"
    _description = "Steadfast Shipment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="New", readonly=True, copy=False)
    carrier_id = fields.Many2one("delivery.carrier", required=True, ondelete="cascade", index=True)
    picking_id = fields.Many2one("stock.picking", required=True, ondelete="cascade", index=True)
    sale_id = fields.Many2one("sale.order", related="picking_id.sale_id", store=True, index=True)
    partner_id = fields.Many2one("res.partner", related="picking_id.partner_id", store=True)
    invoice = fields.Char(index=True)
    consignment_id = fields.Char(index=True, copy=False)
    tracking_code = fields.Char(index=True, copy=False)
    tracking_link = fields.Char(copy=False)
    cod_amount = fields.Float(string="COD Amount")
    delivery_charge = fields.Float(string="Delivery Charge")
    cod_move_id = fields.Many2one("account.move", string="COD Journal Entry", readonly=True, copy=False)
    state = fields.Selection([
        ("pending", "Pending"), ("in_review", "In Review"), ("hold", "Hold"),
        ("delivered_approval_pending", "Delivered - Approval Pending"),
        ("partial_delivered_approval_pending", "Partial Delivered - Approval Pending"),
        ("cancelled_approval_pending", "Cancelled - Approval Pending"),
        ("unknown_approval_pending", "Unknown - Approval Pending"),
        ("delivered", "Delivered"), ("partial_delivered", "Partial Delivered"),
        ("cancelled", "Cancelled"), ("exceptional", "Exceptional"), ("unknown", "Unknown"),
    ], default="pending", tracking=True)
    return_state = fields.Selection([
        ("partial_delivered_return_proccessing", "Partial Delivered - Return Processing"),
        ("partial_delivered_return_rider_assigned", "Partial Delivered - Return Rider Assigned"),
        ("partial_delivered_return_received", "Partial Delivered - Return Received"),
        ("cancelled_return_proccessing", "Cancelled - Return Processing"),
        ("cancelled_return_rider_assigned", "Cancelled - Return Rider Assigned"),
        ("cancelled_return_received", "Cancelled - Return Received"),
    ], tracking=True)
    last_sync = fields.Datetime(readonly=True)
    last_webhook_at = fields.Datetime(string="Last Webhook Update", readonly=True)
    is_terminal = fields.Boolean(compute="_compute_is_terminal", store=True)
    last_response = fields.Text(readonly=True)
    error_message = fields.Text(readonly=True)
    tracking_event_ids = fields.One2many("steadfast.tracking.event", "shipment_id")

    @api.depends("state")
    def _compute_is_terminal(self):
        terminal = {"delivered", "cancelled"}
        for rec in self:
            rec.is_terminal = rec.state in terminal

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") in (False, "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("steadfast.shipment") or "New"
        return super().create(vals_list)

    def action_refresh_status(self):
        for rec in self:
            rec.ensure_one()
            if not rec.consignment_id and not rec.invoice and not rec.tracking_code:
                raise UserError(_("No Steadfast identifier is available."))
            client = rec.carrier_id._steadfast_client()
            try:
                if rec.consignment_id:
                    response = client.status_with_return_by_cid(rec.consignment_id)
                elif rec.tracking_code:
                    response = client.status_by_tracking_code(rec.tracking_code)
                else:
                    response = client.status_by_invoice(rec.invoice)
                rec._apply_status_response(response)
            except SteadfastAPIError as exc:
                rec.write({"error_message": str(exc)})
                raise
        return True

    @staticmethod
    def _steadfast_datetime(value):
        """Convert Steadfast ISO-8601 timestamps to Odoo Datetime values."""
        if not value:
            return False
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return False
        value = value.strip()
        if not value:
            return False
        try:
            # Steadfast commonly returns values such as
            # 2026-10-01T22:20:56.000000Z.
            normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
            return datetime.fromisoformat(normalized).replace(tzinfo=None)
        except (TypeError, ValueError):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return False

    def action_tracking_history(self):
        self.ensure_one()
        if not self.invoice:
            raise UserError(_("This shipment has no invoice/order reference."))
        response = self.carrier_id._steadfast_client().tracking_history_by_invoice(self.invoice)
        self._store_tracking_events(response)
        return {
            "type": "ir.actions.act_window",
            "name": _("Tracking History"),
            "res_model": "steadfast.tracking.event",
            "view_mode": "list,form",
            "domain": [("shipment_id", "=", self.id)],
        }

    def _apply_status_response(self, response, source="api"):
        self.ensure_one()
        payload = response if isinstance(response, dict) else {}
        data = payload.get("data", payload)
        if isinstance(data, list):
            data = data[0] if data and isinstance(data[0], dict) else {}
        if not isinstance(data, dict):
            data = {}

        # Steadfast uses the top-level ``status`` field for the HTTP/API
        # response code in several endpoints (for example ``200``). That
        # value is NOT the parcel state and must never be written to the
        # Selection field below. Parcel details may be wrapped in
        # ``consignment`` or ``data`` depending on the endpoint.
        consignment = payload.get("consignment")
        if not isinstance(consignment, dict):
            consignment = data.get("consignment") if isinstance(data.get("consignment"), dict) else {}

        from .steadfast_client import DELIVERY_STATUSES
        status_candidates = [
            payload.get("delivery_status"),
            payload.get("parcel_status"),
            payload.get("status") if isinstance(payload.get("status"), str) else None,
            consignment.get("status"),
            consignment.get("delivery_status"),
            data.get("delivery_status"),
            data.get("parcel_status"),
            data.get("status") if isinstance(data.get("status"), str) else None,
        ]
        status = next((str(value).strip().lower() for value in status_candidates
                       if isinstance(value, str) and str(value).strip().lower() in DELIVERY_STATUSES), False)

        return_status = (payload.get("return_status") or payload.get("returnStatus") or
                         consignment.get("return_status") or consignment.get("returnStatus") or
                         data.get("return_status") or data.get("returnStatus"))
        tracking_message = (payload.get("tracking_message") or payload.get("message") or
                            consignment.get("tracking_message") or consignment.get("message") or
                            data.get("tracking_message") or data.get("message") or data.get("description"))
        consignment_id = (payload.get("consignment_id") or consignment.get("consignment_id") or
                          data.get("consignment_id"))
        tracking_code = (payload.get("tracking_code") or consignment.get("tracking_code") or
                         data.get("tracking_code"))
        tracking_link = (payload.get("tracking_link") or consignment.get("tracking_link") or
                         data.get("tracking_link"))
        invoice = payload.get("invoice") or consignment.get("invoice") or data.get("invoice")
        old_state = self.state
        vals = {
            "last_response": json.dumps(response, ensure_ascii=False, indent=2),
            "last_sync": fields.Datetime.now(),
            "error_message": False,
        }
        if source == "webhook":
            vals["last_webhook_at"] = fields.Datetime.now()
        if status:
            vals["state"] = str(status).strip().lower()
        if return_status:
            vals["return_state"] = return_status
        if consignment_id:
            vals["consignment_id"] = str(consignment_id)
        if tracking_code:
            vals["tracking_code"] = str(tracking_code)
        if tracking_link:
            vals["tracking_link"] = tracking_link
        if invoice:
            vals["invoice"] = invoice
        self.write(vals)
        picking = self.picking_id
        if picking:
            pvals = {}
            if consignment_id:
                pvals["steadfast_consignment_id"] = str(consignment_id)
            if tracking_code:
                pvals["steadfast_tracking_code"] = str(tracking_code)
            if tracking_link:
                pvals["steadfast_tracking_link"] = tracking_link
            if status:
                normalized = str(status).strip().lower()
                pvals["steadfast_parcel_status"] = normalized
                pvals["steadfast_status_terminal"] = normalized in {"delivered", "cancelled"}
            if tracking_message:
                pvals["steadfast_tracking_message"] = tracking_message
            pvals["steadfast_status_updated_at"] = fields.Datetime.now()
            if pvals:
                picking.write(pvals)
                if status:
                    picking.message_post(body=_("Steadfast parcel status: <b>%s</b>%s") % (status, (" — %s" % tracking_message) if tracking_message else ""))
        self._store_tracking_events(response)
        # If the customer invoice was posted after the shipment was booked,
        # retry the COD receivable reconciliation on every status refresh.
        if self.cod_move_id and self.picking_id:
            self.carrier_id._steadfast_reconcile_cod_invoice(self.picking_id, self.cod_move_id)
        if status and str(status).strip().lower() != (old_state or "").lower():
            event_key = "status:%s:%s" % (str(status).strip().lower(), tracking_message or "")
            exists = self.env["steadfast.tracking.event"].search([("shipment_id", "=", self.id), ("event_hash", "=", event_key)], limit=1)
            if not exists:
                self.env["steadfast.tracking.event"].create({
                    "shipment_id": self.id,
                    "status": str(status).strip().lower(),
                    "event_date": fields.Datetime.now(),
                    "description": tracking_message or False,
                    "raw_json": json.dumps(response, ensure_ascii=False, indent=2),
                    "event_hash": event_key,
                })
            self.message_post(body=_("Steadfast status updated to <b>%s</b>%s.") % (status, (" — %s" % tracking_message) if tracking_message else ""))
        return True

    def _store_tracking_events(self, response):
        self.ensure_one()
        events = []
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, list):
                events = data
            elif isinstance(data, dict):
                for key in ("tracking", "trackings", "history", "events"):
                    if isinstance(data.get(key), list):
                        events = data[key]
                        break
        for event in events:
            if not isinstance(event, dict):
                continue
            status = event.get("status") or event.get("tracking_status") or event.get("name") or "unknown"
            event_key = json.dumps(event, sort_keys=True, ensure_ascii=False)
            exists = self.env["steadfast.tracking.event"].search([("shipment_id", "=", self.id), ("event_hash", "=", event_key)], limit=1)
            if not exists:
                self.env["steadfast.tracking.event"].create({
                    "shipment_id": self.id,
                    "status": status,
                    "event_date": self._steadfast_datetime(
                        event.get("date") or event.get("created_at") or event.get("updated_at")
                    ),
                    "description": event.get("description") or event.get("message") or False,
                    "raw_json": json.dumps(event, ensure_ascii=False, indent=2),
                    "event_hash": event_key,
                })

    def action_create_cod_journal_entry(self):
        for rec in self:
            if not rec.picking_id.steadfast_cod_enabled or not rec.cod_amount:
                raise UserError(_("This shipment has no COD amount to journal."))
            move = rec.carrier_id._steadfast_create_cod_move(rec.picking_id, rec, post=True)
            if not move:
                raise UserError(_("Configure the Steadfast COD Journal, COD Receivable Account and a customer receivable account first."))
        return True

    def action_open_picking(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "stock.picking", "res_id": self.picking_id.id, "view_mode": "form"}

    def action_open_tracking(self):
        self.ensure_one()
        url = self.carrier_id.steadfast_get_tracking_link(self.picking_id)
        if not url:
            raise UserError(_("No customer tracking URL is configured for this carrier."))
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}
