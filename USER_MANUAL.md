- Added backward-compatible `steadfast_auth_token` alias for older carrier views.
18.0.2.0.15

- Added backward-compatible `steadfast_call_back_url` alias for older carrier views.

# Steadfast Delivery — User Manual

**Version: 18.0.2.0.24**

## 1. Purpose
This module connects Odoo 18 Delivery Methods with Steadfast Courier and provides a management interface for the documented Steadfast API operations.

## 2. Installation
Copy the complete `delivery_steadfast` directory into an Odoo 18 addons directory. Restart Odoo, update the Apps list, and install **Steadfast Delivery**. Version 18.0.2.0.24 also loads the module data that creates the default Steadfast Courier delivery method, service product, and COD journal. If the module is already installed, replace the entire module folder and click **Upgrade** in Apps so this data file is loaded.

## 3. Configure the carrier
Inventory → Configuration → Delivery Methods. The module should create a delivery method named **SteadFast Curier** (provider **Steadfast Courier**) automatically. Open that record to configure it. If it is not present after upgrading, click **New** and set Provider to **Steadfast Courier**. Enter:
- API Base URL: `https://portal.packzy.com/api/v1`
- API Key
- Secret Key
- API timeout
- Automatic Status Sync if desired
- Webhook Enabled if you will configure a webhook
- Use Order Total as COD if COD should be based on the sale order total excluding delivery
- Optional Tracking Page URL, using `<tracking_code>` as placeholder

Click **Test Steadfast**. The test uses `/ping`, which does not require credentials.

## 4. Create a shipment
Set the Steadfast carrier on the delivery method/order. On delivery validation, Odoo's carrier integration calls the Steadfast create-order endpoint when the carrier integration level is configured to create shipments.

The module sends invoice/order reference, customer name, phone, address, COD amount and note. Text is pre-cleaned and length-limited to the documented Steadfast limits.


## Delivery price zones (version 18.0.2.0.21+)

Steadfast delivery quotes now choose a route from the customer's shipping address instead of always using the carrier's default route. On a Delivery Order, the suggested route is refreshed when the carrier, destination partner, or pickup location changes. Staff can still correct the route manually if the address is incomplete or a courier classifies a location differently.

In **Inventory → Configuration → Delivery Methods → Steadfast carrier → Steadfast Local Pricing**, configure:
- **Inside Dhaka Base**: rate for Dhaka city.
- **Dhaka → Sub-urban Base**: rate for configured Dhaka suburban destinations.
- **Dhaka → Other District Base**: rate for other districts.
- **Sub-urban → Other District Base** and **Outside Dhaka Same City Base**: rates for those routes.
- **Dhaka City Location Names**: comma-separated city/district names recognized as Dhaka city (default: `Dhaka, Dacca`).
- **Dhaka Suburban Location Names**: comma-separated names recognized as suburban locations (default: `Savar, Ashulia, Tongi, Gazipur, Keraniganj`).

The matching is case-insensitive and uses the shipping partner's City, State, Street, and Street 2 fields. Make sure the customer's **City** field contains the correct location name. If your courier's zone boundaries differ, adjust the location lists and verify the suggested route before booking. The final amount still includes weight surcharge and the configured COD fee.

## 5. Shipment tracking
Open Steadfast Courier → Shipments. Open a shipment and use **Refresh Status** or **Tracking History**. The module supports lookup by consignment ID, invoice and tracking code.

Approval-pending statuses are kept distinct from confirmed `delivered`, `partial_delivered` and `cancelled` statuses.

## 6. Returns
Steadfast Courier → Return Requests. Enter the exact JSON body required by your Steadfast account/API documentation and use **Send Return Request**. The module deliberately does not invent an undocumented payload schema.

## 7. Pickup requests
Steadfast Courier → Pickup Requests. Enter the exact JSON payload and click **Send Pickup Request**.

## 8. Balance and payments
Use the carrier's **Refresh Balance** button for the current balance. Payments can be inspected through the Payments menu or API Tools.

## 9. Fraud check
Steadfast Courier → API Tools → Fraud Score. Enter the customer's phone number.

## 10. Police stations
Use API Tools → Police Stations to retrieve Steadfast's reference list of deliverable thanas/districts.

## 11. Webhook
Enable Webhook on the carrier. Configure Steadfast to call:
`https://YOUR-ODOO-DOMAIN/steadfast/webhook/CARRIER_ID`

The webhook stores the raw JSON and attempts to update a matching shipment.

## 12. API logging
Enable Debug logging on the carrier when troubleshooting. Logs are available to system administrators under Steadfast Courier → API Logs. Secret keys are not written to the log.

## 13. Important statuses
Confirmed outcomes are:
- `delivered`
- `partial_delivered`
- `cancelled`

Statuses ending in `_approval_pending` are intentionally not treated as final accounting outcomes.

## 14. Troubleshooting
- 401: verify API key and secret; do not retry repeatedly.
- 403: verify account status/permissions.
- 422: inspect the returned field errors.
- 429: wait/back off.
- 500: retry the same invoice rather than creating a different invoice.
- No shipment identifier: inspect the API response and API Logs.


## COD Journal Compatibility (18.0.1.0.1)

Steadfast carriers include a **Related Journal** field. This field is intentionally named `related_journal` for compatibility with the previous Steadfast connector. Select the dedicated cash/bank journal that you use to identify and track Steadfast COD-related accounting transactions.

The **Steadfast COD Journal** field is an alias of the same journal and may be used where the interface explicitly describes Steadfast COD accounting. The selected journal is restricted to the current company and to Cash/Bank journals.

If an older inherited Steadfast view already references `related_journal`, version 18.0.1.0.1 restores that field so the carrier form can be validated correctly.

## Local pricing and accounting (18.0.1.0.4)
The Steadfast carrier configuration contains editable local pricing rules for route, included weight, extra-weight increments and the COD/risk percentage. Delivery orders have a local calculator that writes the calculated base charge, weight surcharge, COD fee and total delivery charge onto the delivery.

The carrier can have multiple pickup locations. A delivery order can select a pickup location, and pickup requests can be generated from any configured location.

For accounting, configure a Steadfast COD Journal and a COD Receivable Account. A booked COD shipment can create a draft journal entry that reclassifies the customer receivable to Steadfast COD receivable. Imported Steadfast payment/settlement records can create a draft journal entry that debits the journal's default account and credits the COD receivable account. Review and post entries according to the merchant's accounting policy.

## COD confirmation in 18.0.1.0.7

A Delivery Order using Steadfast now has a dedicated **Confirm Steadfast COD** header button. Clicking it opens a modal showing the order COD amount and the exact amount to be collected. The user must click **Confirm COD Amount** in the modal before the shipment can be sent. Editing the COD amount after confirmation resets the confirmation.


## Release 18.0.2.0.19

This release includes an Odoo 18 compatibility fix for existing stock picking views that reference `carrier_tracking_time`. The field is now provided as a non-stored compatibility field and mirrors the Steadfast tracking status update time.

### Tracking button compatibility (v18.0.2.0.22)
The delivery-order **Track Now** button uses the module's `action_open_steadfast_tracking` action and is shown only for Steadfast deliveries with an available tracking link. If upgrading from an older version, replace the complete `delivery_steadfast` addon folder with this release before restarting Odoo and upgrading the app.

## Upgrade note for version 18.0.2.0.23

This version retains a compatibility handler for older stock transfer views that call `track_parcel`. To ensure the fix is loaded, stop Odoo, replace the entire `delivery_steadfast` folder (do not merge files), restart Odoo, and upgrade the module from Apps. If an old database view remains, the compatibility handler keeps its button valid.
