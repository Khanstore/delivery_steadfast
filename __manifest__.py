{
    "name": "Steadfast Delivery",
    "version": "18.0.2.0.19",
    "category": "Inventory/Delivery",
    "summary": "Steadfast Courier delivery carrier integration for Odoo 18",
    "description": """
Steadfast Courier integration for Odoo 18.

Provides a native delivery.carrier provider plus Steadfast API tools for
shipment booking, bulk booking, tracking, returns, pickups, balance,
payments, police stations, fraud checks and webhooks.
""",
    "author": "Khan Store",
    "website": "https://khan-store.com",
    "license": "LGPL-3",
    "depends": ["account", "delivery", "stock_delivery", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/steadfast_cod_confirm_views.xml",
        "data/ir_cron.xml",
        "views/delivery_carrier_views.xml",
        "views/steadfast_pricing_views.xml",
        "views/steadfast_shipment_views.xml",
        "views/steadfast_tracking_views.xml",
        "views/steadfast_return_views.xml",
        "views/steadfast_pickup_views.xml",
        "views/steadfast_payment_views.xml",
        "views/steadfast_log_views.xml",
        "views/steadfast_tools_views.xml",
        "views/stock_picking_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "delivery_steadfast/static/src/js/stock_picking_status.js",
        ],
    },
    "external_dependencies": {"python": ["requests"]},
    "installable": True,
    "application": True,
}
