# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "SteadFast Courier Service Shipping",
    'description': "Send your shippings through SteadFast and track them online",
    'category': 'Inventory/Delivery',
    'sequence': 305,
    'version': '16.0.1.0',
    'author': "SM Ashraf",
    'website': "https://www.khan-store.com",
    'application': True,
    'depends': ['delivery', 'mail'],
    'data': [
        'data/delivery_steadfast_data.xml',
        # 'data/res.country.state.csv',
        'views/delivery_steadfast_view.xml',
        # 'views/delivery_steadfast_template.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'OEEL-1',
}
