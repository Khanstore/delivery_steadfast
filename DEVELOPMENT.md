# Steadfast Delivery — Developer Manual

**Version: 18.0.1.0.0**

## Architecture

- `models/delivery_carrier.py`: native Odoo `delivery.carrier` provider implementation.
- `models/steadfast_client.py`: HTTP client and all 18 documented endpoints.
- `models/steadfast_shipment.py`: persistent shipment records, status sync and tracking history.
- `models/steadfast_tracking.py`: tracking events.
- `models/steadfast_return.py`: return request UI using exact JSON payloads supplied by the merchant.
- `models/steadfast_pickup.py`: pickup request UI using exact JSON payloads supplied by the merchant.
- `models/steadfast_payment.py`: payment/payout records.
- `models/steadfast_log.py`: API diagnostics.
- `models/steadfast_webhook.py`: webhook event storage.
- `controllers/webhook.py`: public webhook endpoint.
- `models/steadfast_tools.py`: endpoint-by-endpoint API utility wizard.

## Odoo provider contract
Odoo 18's `delivery.carrier` extension pattern requires the provider selection and provider-specific methods. This module implements:

- `steadfast_rate_shipment(order)`
- `steadfast_send_shipping(pickings)`
- `steadfast_get_tracking_link(picking)`
- `steadfast_cancel_shipment(pickings)`

The cancellation method intentionally raises a clear message because the supplied Steadfast documentation does not list a cancellation endpoint.

## API client
`SteadfastClient` centralizes headers, timeout handling, JSON parsing, error handling and logging. Every authenticated request sends `Api-Key`, `Secret-Key`, and POST requests send JSON content type.

`/ping` is sent without credentials.

## Endpoint coverage
1. GET `/ping`
2. POST `/create_order`
3. POST `/create_order/bulk-order`
4. POST `/create_order/bulk-order/extended`
5. GET `/status_by_cid/{consignment_id}`
6. GET `/status_with_return_status_by_cid/{consignment_id}`
7. GET `/status_by_invoice/{invoice}`
8. GET `/status_by_trackingcode/{tracking_code}`
9. GET `/trackings_by_invoice/{invoice}`
10. POST `/create_pickup_request`
11. POST `/create_return_request`
12. GET `/get_return_requests`
13. GET `/get_return_request/{id}`
14. GET `/get_balance`
15. GET `/payments`
16. GET `/payments/{payment_id}`
17. GET `/police_stations`
18. GET `/fraud_check/score/{phone}`

## Bulk booking
The API documentation says bulk booking supports up to 500 parcels. The module's client accepts a payload such as `{"data": [...]}` without rewriting the merchant's item schema.

## Payload safety
The documented create-order fields are normalized to the documented maximum lengths:
- invoice 100
- recipient_name 100
- recipient_phone 40
- recipient_address 490
- note 480

The documented character sanitization is applied before create-order requests.

## Webhook processing
The controller accepts JSON, stores the event, then attempts shipment matching by consignment ID, tracking code or invoice. Because the supplied documentation does not provide a webhook schema, processing is intentionally tolerant and does not assume undocumented keys beyond these common identifiers.

## Scheduled synchronization
A 10-minute cron calls `delivery.carrier.cron_steadfast_sync()` for active Steadfast carriers with automatic synchronization enabled. Status responses are cached by Steadfast for 60 seconds according to the supplied documentation, so the cron is deliberately not aggressive.

## Security
API logs never include the carrier API key or secret key. Credentials are stored on `delivery.carrier` with copy disabled.

## Extending the module
Add new endpoint wrappers to `SteadfastClient`, then expose them through a model/wizard rather than placing HTTP calls directly in views/controllers. Keep carrier-specific behavior in provider methods and persistent shipment state in `steadfast.shipment`.

## Testing
The source package includes Python syntax checks and Odoo test scaffolding. Full Odoo installation tests must be run against an actual Odoo 18 server because this build environment does not contain the Odoo Python package.


## COD Journal Compatibility (18.0.1.0.1)

`delivery.carrier.related_journal` is a `Many2one` to `account.journal` and is company-dependent. Its domain limits selection to the carrier's company and `bank`/`cash` journal types. It preserves compatibility with the previous Steadfast implementation and any existing inherited views that reference the field.

`delivery.carrier.steadfast_cod_journal` is an editable related alias pointing to `related_journal`; it exists to make the purpose of the field explicit in the new connector UI without breaking the legacy field name.

The module therefore declares `account` explicitly in `__manifest__.py`.
