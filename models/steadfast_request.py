# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from flask import jsonify
import binascii
import math
import re
import json
import requests
from lxml import etree
from odoo import fields, _,_lt


class steadFastRequest():

    def __init__(self, debug_logger, api_key, secret_key,  prod_environment):
        self.debug_logger = debug_logger
        if not prod_environment:
            self.url = 'https://staging.ecourier.com.bd/api'
            # self.client_id="7N1aMJQbWm"
            # self.client_secret= "wRcaibZkUdSNz2EI9ZyuXLlNrnAv0TdPUPXMnD39"
            # self.client_email="test@ecourier.com"
            # self.client_password="loveeCourier"
            # self.grant_type="password"
            # self.store_id=55811 # sandbox test store_id 55811

        else:
            self.url = 'https://portal.packzy.com/api/v1'
            self.api_key = api_key
            self.secret_key = secret_key
        self.prod_environment = prod_environment
    # Fixme complete folowing function
    def check_required_value(self, shipper, ship_from, ship_to, order=False, picking=False):
        required_field = {'city': 'City', 'country_id': 'Country', 'phone': 'Phone'}
        # # Check required field for shipper
        # res = [required_field[field] for field in required_field if not shipper[field]]
        # if shipper.country_id.code in ("BD") and not shipper.state_id.code:
        #     res.append('State')
        # if not shipper.street and not shipper.street2:
        #     res.append('Street')
        # if  not shipper.zip:
        #     res.append('ZIP code')
        # if res:
        #     return _("The address of your company is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        # if len(self._clean_phone_number(shipper.phone)) < 10:
        #     return str(eCourier_ERROR_MAP.get('120115'))
        # # Check required field for warehouse address
        # res = [required_field[field] for field in required_field if not ship_from[field]]
        # if ship_from.country_id.code in ('BD') and not ship_from.state_id.code:
        #     res.append('State')
        # if not ship_from.street and not ship_from.street2:
        #     res.append('Street')
        # if not ship_from.zip:
        #     res.append('ZIP code')
        # if res:
        #     return _("The address of your warehouse is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        # if len(self._clean_phone_number(ship_from.phone)) < 10:
        #     return str(eCourier_ERROR_MAP.get('120313'))
        # Check required field for recipient address
        res = [required_field[field] for field in required_field if field != 'phone' and not ship_to[field]]
        if ship_to.country_id.code not in ("BD") and not ship_to.state_id.code:
            res.append('State')
        # The street isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not ship_to.street and not ship_to.street2 :
            res.append('Street')
        # if len(ship_to.street or '') > 35 or len(ship_to.street2 or '') > 35:
        #     return _("eCourier address lines can only contain a maximum of 35 characters. You can split the contacts addresses on multiple lines to try to avoid this limitation.")
        if picking and not order:
            order = picking.sale_id
        phone = ship_to.mobile or ship_to.phone
        if order and not phone:
            phone = order.partner_id.mobile or order.partner_id.phone
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s") % ", ".join(error_lines.product_id.mapped('name'))
        if picking:
            for ml in picking.move_line_ids.filtered(lambda ml: not ml.result_package_id and not ml.product_id.weight):
                return _("The delivery cannot be done because the weight of your product is missing.")
            packages_without_weight = picking.move_line_ids.mapped('result_package_id').filtered(lambda p: not p.shipping_weight)
            if packages_without_weight:
                return _('Packages %s do not have a positive shipping weight.', ', '.join(packages_without_weight.mapped('display_name')))
        # The phone isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not phone and not ship_to._context.get(
            'express_checkout_partial_delivery_address', False
        ):
            res.append('Phone')
        if res:
            return _("The recipient address is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        # The phone isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not ship_to._context.get(
            'express_checkout_partial_delivery_address', False
        ) and len(self._clean_phone_number(phone)) < 11:
            return str(eCourier_ERROR_MAP.get('120213'))
        return False


    def send_shipping(self, invoice, recipient_name, recipient_phone, recipient_address, cod_amount, note):
        url= self.url + "/create_order"

        Headers= {
            "Api-Key": self.api_key,
            "Secret-Key": self.secret_key,
            "Content-Type": "application/json"
        }
        json_data = {
            "invoice": invoice,
            #TODO get order id here
            "recipient_name": recipient_name,
            "recipient_phone": recipient_phone,
            "recipient_address":recipient_address,
            "cod_amount": cod_amount,
            "note": note       }
        response = requests.post(url, data=json.dumps(json_data), headers=Headers)

        return response

    def steadfast_rate_request(self,order):
        #fixme add optional products for rate calculations
        # steadFast does not have an api to rate request so it is managed manually here
        lines=order.order_line
        destination=order.partner_shipping_id.state_id
        weight=0
        for line in lines:
            line_weight=line.product_id.weight*line.product_uom_qty
            weight=line_weight+weight

        if weight <= 0.5:
            price = 110 # 110 tk for <.5kg
            weight = 0
        elif weight <= 1:
            price = 130 # 130 tk for <.1kg
            weight = 0
        else:
            weight = weight - 1
            price = 130 + weight // 1 * 20 # 20tk/kg
        if weight % 1 > 0:
            price = price + 20  # 20tk for less than 1kg
        response={'type':'success','code':200,'data':{'final_price':price}}



        return response
    def _item_data(self, line, weight, price):
        return {
            'Description': line.name,
            'Quantity': max(int(line.product_uom_qty), 1),  # the USPS API does not accept 1.0 but 1
            'Value': price,
            'NetPounds': weight['pound'],
            'NetOunces': round(weight['ounce'], 0),
            'CountryOfOrigin': line.warehouse_id.partner_id.country_id.name or ''
        }

    def check_consignment_by_id(self,consignment_id):
        url=self.url+ "/ status_by_cid /"+consignment_id


        Method: GET
