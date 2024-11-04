# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from email.policy import default

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

    def _get_steadfast_service_types(self):
        #     pathao delivery types 48 for normal delivery
        return [
            ('48', 'Normal Delivery'),
            # ('11', 'Pathao Standard'),
            ]
    delivery_type = fields.Selection(selection_add=[
        ('steadfast', "SteadFast")
    ], ondelete={'steadfast': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    steadfast_api_key=fields.Char("API Key ID") #"7N1aMJQbWm"
    steadfast_secret_key =fields.Char("Secret Key") # "wRcaibZkUdSNz2EI9ZyuXLlNrnAv0TdPUPXMnD39"

    def steadfast_rate_shipment(self, order):
        superself = self.sudo()
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

    def steadfast_send_shipping(self,piking_id):
        res = []
        superself = self.sudo()
        req = steadFastRequest(self.log_xml, superself.steadfast_api_key, superself.steadfast_secret_key, superself.prod_environment)

        partner=piking_id.partner_id
        #steadFast supports letters,Numbers,dashes in Invoice String
        invoice=piking_id.name.replace("/","-")
        recipient_name=partner.name
        if partner.mobile:
            recipient_phone=partner.mobile
        else:
            recipient_phone = partner.phone
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
        cod_amount=100
        note="note"
        # Fixme
        response=req.send_shipping(invoice, recipient_name, recipient_phone, recipient_address, cod_amount, note)
        result = response.json()
        # response={'status': 200, 'message': 'Consignment has been created successfully.', 'consignment': {'consignment_id': 106743223, 'invoice': 'WH-OUT-00026', 'tracking_code': '65CC5B783A7', 'recipient_name': 'Oscar Morgan', 'recipient_phone': '01777777777', 'recipient_address': '317 Fairchild Dr, Fairfield, California,', 'cod_amount': 100, 'status': 'in_review', 'note': 'note', 'created_at': '2024-11-03T11:01:59.000000Z', 'updated_at': '2024-11-03T11:01:59.000000Z'}}
        # result = response
        if 'errors' in result.keys():
            error=[i for i in result['errors']]
            msg =result['errors'][error[0]][0]

            raise UserError(msg.__str__())

        order = piking_id.sale_id
        company = order.company_id or piking_id.company_id or self.env.company
        currency_order = piking_id.sale_id.currency_id
        if not currency_order:
            currency_order = piking_id.company_id.currency_id
        # Fixme Price =??
        price=123
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

        return res

    def steadfast_get_tracking_link(self,picking_id):
        return 'https://steadfast.com.bd/t/%s' % picking_id.carrier_tracking_ref
    # #Todo following function get errors
    # def pathao_get_parcel_status(self,consignment_id):
    #     superself = self.sudo()
    #     req = pathaoRequest(self.log_xml, superself.pathao_client_id, superself.pathao_client_secret,
    #                         superself.pathao_client_email, superself.pathao_client_password, superself.store_id,
    #                         self.prod_environment)
    #     url = req.url + "/aladdin/api/v1/orders/{"+ consignment_id +"}/info"
    #     token = req.pathao_get_token()
    #
    #     Headers= {
    #         "Authorization": "Bearer "+token,
    #         "Content - Type": "application/json",
    #         "Accept": "application/json"
    #     }
    #     payloads={}
    #     response=requests.get(url,headers=Headers,data=json.dumps(payloads))
    #     if response.json()['type']=="error":
    #         raise UserError(response.json()['message'].__str__())
    #     else:
    #         return response



class stockPicking(models.Model):
    _inherit = "stock.picking"

    def get_tracking_link(self):
        self.ensure_one()
        url=self.carrier_tracking_url
        return {'name': 'Go to website',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': url
                }