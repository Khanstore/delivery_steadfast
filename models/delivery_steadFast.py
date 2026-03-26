# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from email.policy import default
import logging

_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json
from . steadfast_request import steadFastRequest
import requests


import math
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    module_delivery_steadfast = fields.Boolean("SteadFast Courier Connector")


class ProviderSteadFast(models.Model):
    _inherit = 'delivery.carrier'

    related_journal = fields.Many2one('account.journal', string='Related Journal')



    def _get_steadfast_service_types(self):
        #     pathao delivery types 48 for normal delivery
        return [
            ('48', 'Normal Delivery'),
            # ('11', 'steadfast Standard'),
            ]
    delivery_type = fields.Selection(selection_add=[
        ('steadfast', "SteadFast")
    ], ondelete={'steadfast': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    steadfast_api_key=fields.Char("API Key ID")
    steadfast_secret_key =fields.Char("Secret Key")
    steadfast_call_back_url=fields.Char("Call back URL")
    steadfast_auth_token=fields.Char("Auth Token")


    def steadfast_rate_shipment(self, order):
        superself = self.sudo()
        # todo this line used to test Webhook, uncomment to use
        # self.send_test_webhook()
        req = steadFastRequest(self.log_xml, self.steadfast_api_key, self.steadfast_secret_key, self.prod_environment)
        ResCurrency = self.env['res.currency']

        response=req.steadfast_rate_request(order)
        result=response
        data = {}
        if result['type']=='success' and result['code']==200:
            data['price']=result['data']['final_price']
            data['success']=True
            data['error_message']=False
            data['warning_message']=False
        else:
            return False

        return data
    #  Fixme following lines are for testing webhook, uncomment to use
    # def send_test_webhook(self):
    #     for order in self:
    #         # Use real picking/tracking ID if available
    #         # picking = order.picking_ids[:1]
    #         # tracking_id = picking.carrier_tracking_ref if picking else order.id
    #
    #         data={
    #             "notification_type": "delivery_status",
    #             "consignment_id": 162802040,
    #             "invoice": "INV-67890",
    #             "cod_amount": 1500.00,
    #             "status": "Delivered",
    #             "delivery_charge": 100.00,
    #             "tracking_message": "Your package has been delivered successfully.",
    #             "updated_at": "2025-03-02 12:45:30"
    #         }
    #
    #         url = 'http://localhost:8070/delivery/steadfast/callback'
    #         headers = {
    #             'Content-Type': 'application/json',
    #             'Authorization': 'Bearer supersecrettoken123'  # 👈 match the token
    #         }
    #
    #         try:
    #             resp = requests.post(url, json=data, headers=headers, timeout=10)
    #             resp.raise_for_status()
    #             _logger.info("Webhook sent successfully: %s", resp.json())
    #         except Exception as e:
    #             _logger.exception("Failed to send webhook")
    def steadfast_send_shipping(self,picking_id):
        res = []
        superself = self.sudo()
        req = steadFastRequest(self.log_xml, superself.steadfast_api_key, superself.steadfast_secret_key, superself.prod_environment)

        partner=picking_id.partner_id
        #steadFast supports letters,Numbers,dashes in Invoice String
        invoice=picking_id.name.replace("/","-")
        recipient_name=partner.name
        if partner.mobile:
            recipient_phone=partner.mobile
            alternative_phone = partner.phone if partner.phone else ""
        else:
            recipient_phone = partner.phone
            alternative_phone = ""
        recipient_email=partner.email if partner.email else ""
        recipient_address=""
        if partner.street:
            recipient_address=partner.street + ", "
        if partner.street2:
            recipient_address = recipient_address +partner.street2 + ", "
        if partner.city:
            recipient_address = recipient_address + partner.city+ ", "
        if partner.state_id:
            recipient_address = recipient_address + partner.state_id.name+ ", "
        #todo set COD Amount Here
        # for online orders Check if payment method COD is selected
        payment_transaction = self.env['payment.transaction'].search([('reference', '=', picking_id.sale_id.name)])
        payment_provider=payment_transaction.provider_id
        cod_amount = picking_id.cod_amount if picking_id.is_cash_on_delivery else 0

        # if payment_provider.id:
        #
        #     provider_xml_id=payment_provider.get_external_id()[payment_provider.id]
        #     # here to varify COD transaction method
        #     if provider_xml_id=='payment.payment_provider_transfer':
        #         cod_amount=picking_id.sale_id.amount_total
        # else:
        #     cod_amount=0
        note="note"
        # Fixme
        item_description="Book"
        data={'invoice': invoice,
              'recipient_name': recipient_name,
              'recipient_phone': req.convert_phone_number(recipient_phone),
              'alternative_phone': req.convert_phone_number(alternative_phone),
              'recipient_email': recipient_email,
              'recipient_address': recipient_address,
              'cod_amount': cod_amount,
              'note': note,
              'item_description': item_description,
              'delivery_type': 0,# 0 for home delivery, 1 for office delivery

        }
        response=req.send_shipping(data)
        result = response.json()
        # response={'status': 200, 'message': 'Consignment has been created successfully.', 'consignment': {'consignment_id': 106743223, 'invoice': 'WH-OUT-00026', 'tracking_code': '65CC5B783A7', 'recipient_name': 'Oscar Morgan', 'recipient_phone': '01777777777', 'recipient_address': '317 Fairchild Dr, Fairfield, California,', 'cod_amount': 100, 'status': 'in_review', 'note': 'note', 'created_at': '2024-11-03T11:01:59.000000Z', 'updated_at': '2024-11-03T11:01:59.000000Z'}}
        # result = response
        if 'errors' in result.keys():
            error=[i for i in result['errors']]
            msg =result['errors'][error[0]][0]

            raise UserError(msg.__str__())

        order = picking_id.sale_id
        company = order.company_id or picking_id.company_id or self.env.company
        currency_order = picking_id.sale_id.currency_id
        if not currency_order:
            currency_order = picking_id.company_id.currency_id
        # Fixme Price =??
        price=cod_amount
        # price = float(result['data']['delivery_fee'])
        carrier_tracking_ref = result['consignment']['tracking_code']
        # following lines for sending message, since odoo sents message automatically for i in is not longer needed:

        # logmessage = _("Shipment created into Pathao<br/>"
        #                "<b>Tracking Number: %s") % (
        #              carrier_tracking_ref)
        # if picking.sale_id:
        #     for pick in picking.sale_id.picking_ids:
        #         pick.message_post(body=logmessage)
        # else:
        #     picking.message_post(body=logmessage)
        shipping_data = {
            'exact_price': price,
            'tracking_number': carrier_tracking_ref}
        res = res + [shipping_data]
        picking_id.consignment_id= result['consignment']['consignment_id']
        return res

    def steadfast_get_tracking_link(self, picking):
        return 'https://steadfast.com.bd/t/' + picking.carrier_tracking_ref



    def tracking_result(self, tracking_id):
        ''' Track the package to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of dictionaries (one per picking) containing of the form::
                         { 'exact_price': price,
                           'tracking_number': number }
                           # TODO missing labels per package
                           # TODO missing currency
                           # TODO missing success, error, warnings
        '''
        self.ensure_one()
        if hasattr(self, '%s_tracking_result' % self.delivery_type):
            return getattr(self, '%s_tracking_result' % self.delivery_type)(tracking_id)

    def steadfast_tracking_result(self, tracking_id):
        res = []
        superself = self.sudo()
        req = steadFastRequest(self.log_xml, superself.steadfast_api_key, superself.steadfast_secret_key,
                               superself.prod_environment)
        return req.track_by_code(tracking_id)

def track_parcel(self,picking_id):
        return 'https://steadfast.com.bd/t/%s' % picking_id.carrier_tracking_ref




class stockPicking(models.Model):
    _inherit = "stock.picking"
    cod_amount=fields.Float(string='COD Amount',  default=0.0)
    carrier_tracking_status=fields.Char("Tracking Status",default="N/A")
    carrier_tracking_time=fields.Datetime(string='Tracked On')
    tracking_status_changed_on=fields.Datetime(string='Status Changed On')
    consignment_id = fields.Integer("Consignment ID")

    def get_tracking_link(self):
        self.ensure_one()
        url=self.carrier_tracking_url
        return {'name': 'Go to website',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': url
                }
    def track_parcel(self):
        tracking_id=self.carrier_tracking_ref
        result=self.carrier_id.tracking_result(tracking_id)
        self.carrier_tracking_status=result["delivery_status"]
        if result['status_on']:
            self.tracking_status_changed_on=result["status_on"]
        self.carrier_tracking_time=result["tracking_time"]