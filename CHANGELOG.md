# Changelog

## 18.0.1.0.13
- Fixed Steadfast tracking-history ISO-8601 timestamps such as `2026-10-01T22:20:56.000000Z` being written directly to Odoo Datetime fields.
- Steadfast COD journal entries are now posted automatically when created from a confirmed COD shipment.
- Added invoice receivable reconciliation so a posted customer invoice becomes paid/partially paid against the COD reclassification, while the amount remains in the configured Steadfast COD receivable account until settlement.
- Existing COD journal entries are re-used and reconciled when the journal action is run again.
- Steadfast payment import now safely parses ISO-8601 payment timestamps.


## 18.0.1.0.12
- Intercepted Odoo standard Send to Shipper for Steadfast so COD confirmation opens before carrier send_shipping.
- Removed the path where the carrier-level confirmation error could be reached by the normal button.

## 18.0.1.0.10

- Reworked Steadfast COD flow so **Send to Steadfast** always opens the confirmation prompt for unconfirmed COD deliveries.
- Removed the header visibility condition that hid the Send button before confirmation.
- Placed the Steadfast Delivery/COD section directly after the Delivery Order carrier field so it is reliably visible in Odoo 18.
- Initialize editable COD amount on picking creation when Steadfast is selected.

## 18.0.1.0.6
- Added a prominent Confirm Steadfast COD button to the delivery-order header.
- COD confirmation is now logged in the delivery chatter.
- Changing the COD amount after confirmation resets the confirmation.
- Confirmation fills the order COD amount when the amount is still empty.

# Change Log

## 18.0.1.0.1 — COD Journal Compatibility Fix
- Restored the `delivery.carrier.related_journal` field used by the earlier Steadfast connector.
- Added `Steadfast COD Journal` as an editable alias of `related_journal`.
- Added `account` as an explicit module dependency because the carrier now references `account.journal`.
- Exposed the dedicated COD journal in the Steadfast carrier configuration.
- Preserved all functionality from 18.0.1.0.0.

## 18.0.1.0.0 — Initial release
- Native Odoo 18 `delivery.carrier` provider named **Steadfast Courier**.
- Implemented all 18 endpoints listed in the supplied Steadfast API documentation.
- Added single shipment creation and Odoo delivery integration.
- Added tracking by consignment ID, invoice and tracking code.
- Added tracking history and return-aware status support.
- Added pickup/return request interfaces using merchant-supplied JSON payloads because the supplied documentation does not specify those request schemas.
- Added balance, payments, police stations and fraud-score tools.
- Added webhook endpoint and automatic status synchronization.
- Added API logging, error handling, timeout handling and rate-limit messages.
- Added User Manual and Developer Manual.


## 18.0.1.0.3
- Fixed successful Steadfast create-order responses where consignment data is nested under `consignment`.
- Store the Steadfast `tracking_link` returned by the API.
- Added Steadfast COD controls and COD amount confirmation on delivery orders.
- Added product names and quantities to Steadfast shipment notes.
- Sanitized invoice references to Steadfast's allowed characters only.


## 18.0.1.0.4
- Added Steadfast local pricing calculator with editable route, weight and COD rules.
- Added configurable pickup locations and pickup-request UI.
- Added Steadfast icon to the application menu.
- Added COD receivable reclassification into the configured Steadfast journal as a draft journal entry.
- Imported Steadfast payment/settlement records can now create corresponding draft journal entries.
- Added delivery-order charge breakdown and pickup location selection.

## 18.0.1.0.5
- Fixed Odoo 18 carrier-view validation caused by using `account.account.company_id` in the COD account domain.
- Added signed Steadfast webhook verification using Bearer token + HMAC-SHA256.
- Added webhook idempotency handling and persisted webhook events/errors.
- Delivery status, consignment ID, tracking code, tracking link and tracking message are mirrored to the Delivery Order.
- Added automatic status refresh when a non-terminal Steadfast Delivery Order form is opened, with a manual refresh button and scheduled fallback sync.
- `payment_request` webhook events can fetch the authoritative payment and create the configured draft journal entry.
