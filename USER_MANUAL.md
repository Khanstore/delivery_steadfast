- Added backward-compatible `steadfast_auth_token` alias for older carrier views.
18.0.2.0.15

- Added backward-compatible `steadfast_call_back_url` alias for older carrier views.

# Steadfast Delivery — User Manual

**Version: 18.0.1.0.0**

## 1. Purpose
This module connects Odoo 18 Delivery Methods with Steadfast Courier and provides a management interface for the documented Steadfast API operations.

## 2. Installation
Copy the complete `delivery_steadfast` directory into an Odoo 18 addons directory. Restart Odoo, update the Apps list, and install **Steadfast Delivery**.

## 3. Configure the carrier
Inventory → Configuration → Delivery Methods → New.

Set Provider to **Steadfast Courier**. Enter:
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
