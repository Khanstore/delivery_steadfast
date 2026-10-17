# Changelog

## 18.0.2.0.26
- Added configurable Steadfast delivery-charge ceiling: no rounding, ceil to 5, or ceil to 10.
- Applied the ceiling to both checkout delivery-rate calculation and the delivery charge stored when booking a shipment.


## 18.0.2.0.25 — 2026-10-17
- Fixed the actual missing Delivery Methods record problem.
- Added an idempotent upgrade/install hook that ensures the SteadFast Courier delivery carrier exists and is active.
- The hook restores an archived carrier and recreates the carrier if it is missing, without overwriting existing API credentials or pricing configuration.
- Added fallback creation of the delivery service product and COD journal when their records are missing.
- Kept the provider selection as `steadfast` so existing Steadfast functionality remains compatible.

## 18.0.2.0.24 — 2026-10-17
- Fixed the missing Steadfast delivery method: added `data/delivery_steadfast_data.xml` to the module manifest so the default `delivery.carrier` record is loaded during installation/upgrade.
- The carrier record creates the Steadfast Courier delivery method and its required service product and COD journal when they do not already exist.
- Kept the tracking compatibility method and location-based delivery pricing fixes.

## 18.0.2.0.23 — 2026-10-17
- Added a backward-compatible `stock.picking.track_parcel()` handler so legacy inherited views do not block module upgrades.
- The compatibility handler delegates to the current Steadfast tracking action.
- Retained route-based local delivery pricing and the current tracking button implementation.

## 18.0.2.0.22 - 2026-10-17
- Fixed the legacy delivery-order tracking button to call the implemented `action_open_steadfast_tracking` method instead of the missing `track_parcel` method.
- Hide the legacy Track Now button unless the delivery uses Steadfast and has a tracking link.
- Retained route-based delivery pricing for inside Dhaka, suburban Dhaka, outside Dhaka and other configured destinations.

## 18.0.2.0.21 — 2026-10-17
- Fixed delivery pricing so the sales-order carrier quote uses the destination's detected route instead of always using the carrier's default route.
- Delivery Orders now select a route from the shipping address and selected pickup city; changing the carrier, customer/destination, or pickup location recalculates the suggested route.
- Added configurable, comma-separated Dhaka city and Dhaka suburban location names to Steadfast Local Pricing settings.
- Kept the route field editable so staff can manually correct a location when the customer's address is incomplete or unusual.

# Changelog

## 18.0.2.0.20 — 2026-10-07
- Added automatic Steadfast shipment booking after a Delivery Order is successfully validated.
- The booking runs only after Odoo reaches the `done` state, so Immediate Transfer and Backorder wizards are handled normally.
- On validation, an unconfirmed COD amount is automatically confirmed and the current COD amount is sent to Steadfast.
- Existing duplicate-shipment protection remains in place.


## 18.0.2.0.19 — 2026-10-06
- Fixed Odoo 18 stock picking view upgrade failure caused by existing/inherited delivery views referencing the missing `carrier_tracking_time` field.
- Added a non-stored compatibility field on `stock.picking`, mapped to the Steadfast status update timestamp.
- Preserved the existing `carrier_tracking_status` compatibility field and Steadfast tracking flow.
- Bumped the module version and ZIP release suffix.

- Added backward-compatible `stock.picking.tracking_status_changed_on` alias for older tracking views; it mirrors `steadfast_status_updated_at` without creating a database column.
- Fixed module upgrade failure caused by inherited delivery-order views referencing missing `stock.picking.carrier_tracking_status`; restored it as a non-stored compatibility field mirroring the Steadfast parcel status.
- Added backward-compatible `steadfast_auth_token` alias for older carrier views.
18.0.2.0.15

- Added backward-compatible `steadfast_call_back_url` alias for older carrier views.


## 18.0.2.0.14

- Fixed module upgrade failure caused by `delivery.carrier.related_journal` changing from an existing integer Many2one column to Odoo 18 company-dependent JSONB storage.
- Restored `related_journal` as a normal Many2one so existing Steadfast journal IDs upgrade safely without a database column conversion.
# Changelog

## 18.0.2.0.13
- Changed the default Steadfast COD amount to use the full Sale Order `amount_total`, so the customer COD includes the delivery charge and applicable taxes instead of product-only value.
- Updated the Steadfast carrier rate/COD calculation and Delivery Order COD default to use the same full order total.


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
