- Added backward-compatible `steadfast_auth_token` alias for older carrier views.
18.0.2.0.15

- Added backward-compatible `steadfast_call_back_url` alias for older carrier views.

# delivery_steadfast

Odoo 18 delivery carrier integration for Steadfast Courier.

## Version
18.0.1.0.0

## Scope
Implements the Odoo `delivery.carrier` provider pattern and the Steadfast API endpoints documented in the supplied Steadfast API document. Odoo's delivery framework calls provider-specific methods such as `steadfast_rate_shipment`, `steadfast_send_shipping`, `steadfast_get_tracking_link`, and `steadfast_cancel_shipment`; the module follows that extension model. Odoo 18 documents the same provider-extension pattern. 

## Important API-documentation limitation
The supplied document lists the 18 endpoints, authentication, status values, response codes and the single-order payload example. It does not expose the exact JSON request schemas for `create_pickup_request` and `create_return_request`. The module therefore exposes those operations through JSON payload fields/API Tools instead of inventing undocumented fields.

## Installation
1. Copy the `delivery_steadfast` folder into an Odoo 18 addons path.
2. Restart Odoo.
3. Update Apps List.
4. Install **Steadfast Delivery**.
5. Go to Inventory → Configuration → Delivery Methods and create a carrier with Provider = Steadfast Courier.
6. Enter API Key and Secret Key and click Test Steadfast.

## Shipment flow
Configure the carrier and a delivery product. Add the carrier to a sales order. With Odoo's `Get Rate and Create Shipment` integration level, validating a delivery order calls the Steadfast booking method and stores the returned consignment/tracking identifiers.

## API tools
The API Tools wizard exposes ping, all documented GET lookups, pickup/return POST calls, and paginated list/detail operations. Pickup and return POST bodies are intentionally editable JSON because their schemas are not present in the supplied document.

## Webhook
`POST /steadfast/webhook/<carrier_id>` accepts JSON and stores the event. It attempts to match by consignment ID, tracking code or invoice and applies a supplied status payload to the shipment.


### 18.0.1.0.1 compatibility note

This release restores the legacy `related_journal` field used by the earlier Steadfast connector for the dedicated COD journal.

### Webhook setup
Configure the carrier's **Webhook Enabled** and optional **Webhook Auth Token** fields. In Steadfast, use the public HTTPS URL formed from your Odoo domain plus the displayed **Webhook Endpoint Path**, for example `https://your-domain.example/steadfast/webhook/12`. When a token is configured, the module validates the `Authorization: Bearer <token>` header and `X-Signature` HMAC-SHA256 of the raw JSON body. `Idempotency-Key` is used to ignore duplicate deliveries. Delivery-status events update the linked shipment and Odoo Delivery Order; `payment_request` events can fetch the payment and create the configured draft journal entry.
