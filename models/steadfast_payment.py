import json
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SteadfastPayment(models.Model):
    _name = "steadfast.payment"
    _description = "Steadfast Payment / Settlement"
    _order = "id desc"

    name = fields.Char(required=True)
    carrier_id = fields.Many2one("delivery.carrier", required=True, ondelete="cascade")
    payment_id = fields.Char(index=True)
    payment_date = fields.Datetime()
    amount = fields.Float()
    page = fields.Integer(default=1)
    journal_entry_id = fields.Many2one("account.move", string="Related Journal Entry", readonly=True, copy=False)
    journal_state = fields.Selection(related="journal_entry_id.state", string="Journal State")
    response_json = fields.Text(readonly=True)

    def action_refresh(self):
        for rec in self:
            if not rec.payment_id:
                raise UserError(_("Enter a Steadfast payment ID."))
            response = rec.carrier_id._steadfast_client().get_payment(rec.payment_id)
            rec.response_json = json.dumps(response, ensure_ascii=False, indent=2)
            rec._update_from_api_item(response.get("data", response) if isinstance(response, dict) else {})
        return True

    def action_load_list(self):
        self.ensure_one()
        response = self.carrier_id._steadfast_client().get_payments(self.page)
        self.response_json = json.dumps(response, ensure_ascii=False, indent=2)
        records = self.create_from_api(self.carrier_id, response)
        if records:
            return {"type": "ir.actions.act_window", "name": _("Payments / Settlements"), "res_model": "steadfast.payment", "view_mode": "list,form", "domain": [("id", "in", records.ids)]}
        return True

    @staticmethod
    def _steadfast_datetime(value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return False
        try:
            normalized = value.strip()
            normalized = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
            return datetime.fromisoformat(normalized).replace(tzinfo=None)
        except (TypeError, ValueError):
            return False

    def _update_from_api_item(self, item):
        if not isinstance(item, dict):
            return
        self.payment_date = self._steadfast_datetime(item.get("payment_date") or item.get("date") or item.get("created_at")) or self.payment_date
        self.amount = item.get("amount") or item.get("payment_amount") or self.amount

    def action_create_journal_entry(self):
        for rec in self:
            if rec.journal_entry_id:
                continue
            journal = rec.carrier_id.related_journal
            cod_account = rec.carrier_id.steadfast_cod_receivable_account
            if not journal or not cod_account or not journal.default_account_id:
                raise UserError(_("Configure the Steadfast COD Journal, its default account, and the COD Receivable Account first."))
            move = self.env["account.move"].create({
                "move_type": "entry",
                "journal_id": journal.id,
                "date": fields.Date.context_today(self),
                "ref": _("Steadfast Payment %s") % (rec.payment_id or rec.name),
                "line_ids": [
                    (0, 0, {"name": _("Steadfast Settlement"), "account_id": journal.default_account_id.id, "debit": rec.amount, "credit": 0.0}),
                    (0, 0, {"name": _("Steadfast COD Receivable Settlement"), "account_id": cod_account.id, "debit": 0.0, "credit": rec.amount}),
                ],
            })
            rec.journal_entry_id = move.id
        return True

    @api.model
    def create_from_api(self, carrier, response):
        records = []
        data = response.get("data", response) if isinstance(response, dict) else []
        if isinstance(data, dict):
            data = data.get("payments", data.get("data", []))
        if not isinstance(data, list):
            return self.browse()
        for item in data:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or item.get("payment_id") or "")
            if not pid:
                continue
            rec = self.search([("carrier_id", "=", carrier.id), ("payment_id", "=", pid)], limit=1)
            vals = {
                "name": pid, "carrier_id": carrier.id, "payment_id": pid,
                "payment_date": self._steadfast_datetime(item.get("payment_date") or item.get("date") or item.get("created_at")),
                "amount": item.get("amount") or item.get("payment_amount") or 0.0,
                "response_json": json.dumps(item, ensure_ascii=False, indent=2),
            }
            rec = rec or self.create(vals)
            if rec:
                rec._update_from_api_item(item)
                # Reflect imported Steadfast payment/settlement in the configured journal as a draft entry.
                rec.action_create_journal_entry()
            records.append(rec)
        return self.browse([r.id for r in records])
