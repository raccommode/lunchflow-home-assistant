# Lunch Flow for Home Assistant

[![Validate](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/validate.yml)
[![Tests](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

A read-only Home Assistant custom integration for your [Lunch Flow](https://lunchflow.app) bank accounts. It uses the Lunch Flow Personal REST API and creates account balance, transaction, and supported investment-holdings sensors.

This project is an independent community integration and is not affiliated with or endorsed by Lunch Flow.

## One-click setup

First, open this repository in HACS and install Lunch Flow:

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=raccommode&repository=lunchflow-home-assistant&category=integration)

After HACS finishes installing the integration, restart Home Assistant. Then start the Lunch Flow setup:

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=lunchflow)

## Features

- UI setup with a Lunch Flow Personal API key
- One Home Assistant device per bank account
- Current balance sensor with the account currency
- Recent transaction count sensor
- Latest transaction amount with merchant, description, date, ID, and pending status as attributes
- Total investment holdings value for supported providers
- Optional currency conversion, including CAD, EUR, and USD, for same-unit aggregation
- Configurable polling interval, transaction history range, and pending-transaction inclusion
- Automatic reauthentication flow if Lunch Flow rejects the saved key
- No write operations: the integration only calls `GET` endpoints

## Requirements

- Home Assistant 2025.2.0 or newer
- A Lunch Flow account with connected bank accounts
- A Lunch Flow API destination and Personal API key

In Lunch Flow, go to **Destinations → Add Destination → API**. Copy the generated API key and use the destination's Account Access settings to choose which accounts Home Assistant may read.

## Installation with HACS

Click the button to add this repository to HACS automatically:

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=raccommode&repository=lunchflow-home-assistant&category=integration)

Then select **Download**, wait for HACS to finish, and restart Home Assistant.

If the button is unavailable, add `https://github.com/raccommode/lunchflow-home-assistant` manually under **HACS → Custom repositories** and select **Integration** as the category.

## Manual installation

1. Copy `custom_components/lunchflow` into the `custom_components` directory in your Home Assistant configuration directory.
2. Restart Home Assistant.

## Configuration

After installing and restarting Home Assistant, click the button to start the Lunch Flow configuration flow:

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=lunchflow)

Alternatively, go to **Settings → Devices & services → Add Integration**, search for **Lunch Flow**, and paste the Personal API key from your Lunch Flow API destination.

Only one Lunch Flow config entry is needed. Every account exposed by the API destination is discovered automatically.

### Options

Open the Lunch Flow integration and select **Configure** to change:

| Option | Default | Range | Description |
| --- | ---: | ---: | --- |
| Update interval | 30 minutes | 5–1440 | How often Home Assistant polls Lunch Flow. |
| Transaction history | 30 days | 1–365 | Date range used for transaction sensors. |
| Include pending transactions | Enabled | — | Includes unposted transactions returned by Lunch Flow. |
| Target currency | Disabled | Supported currencies | Adds separate monetary sensors in your chosen currency, including CAD, EUR, and USD. Original sensors remain unchanged. |

Changing an option reloads the integration automatically.

### Currency conversion and aggregation

To combine accounts held in different currencies:

1. Open **Settings → Devices & services → Lunch Flow → Configure**.
2. Set **Target currency**, for example **CAD - Canadian dollar**, and save.
3. Use each account's **Converted balance (CAD)** sensor in your dashboard or a **Combine the state of several sensors** helper with **Sum** selected. All selected converted sensors have the same `CAD` unit.

Conversion also creates **Converted last transaction** and, where available, **Converted holdings value** sensors. The original Balance, Last transaction, and Holdings value sensors keep their original currencies and entity IDs. Transaction counts are not converted. Avoid including both original and converted versions of an account in the same total, or adding holdings to balances that already include those holdings.

Rates come from the [Frankfurter v1 API](https://frankfurter.dev/v1/), based on daily reference rates. No additional API key is needed. Home Assistant downloads one public EUR-based table for all accounts and performs cross-currency calculations locally. Rates are cached in memory for six hours. Converted attributes include `original_amount`, `original_currency`, `exchange_rate`, `exchange_rate_date`, and `exchange_rate_source`.

These are reference valuations, not live trading quotes or your bank's final exchange rate. A last transaction is converted at the latest reference rate, not the rate on its transaction date. Calculations retain decimal precision; the displayed amount is rounded by Home Assistant.

During a rate-service outage, cached reference rates may be used for up to seven calendar days from their reference date, allowing for weekends and holidays. Beyond that, or if a source currency is unsupported, the affected converted sensors become unavailable; original sensors still work. Same-currency values remain usable without an external rate. The Sum helper ignores unavailable inputs and can therefore show a partial total. If you need an all-accounts total, use a template sensor with an availability check requiring every input to be numeric; do not substitute zero for unavailable accounts.

Changing the target currency creates currency-specific converted entities so that different units never share the same entity history. Previous converted entities are no longer updated and may remain as unavailable registry entries; switching back reuses them. Select the new currency's entities in existing aggregation helpers. Setting **Target currency** back to **Disabled** stops rate requests and removes the converted sensors from active use.

## Entities

Each account is represented as a device and normally exposes:

| Entity | State | Additional data |
| --- | --- | --- |
| Balance | Current monetary balance | Institution, provider, and account status |
| Transaction count | Transactions in the configured date range | — |
| Last transaction | Latest transaction amount | ID, date, merchant, description, and pending status |
| Holdings value | Total investment value | Holding count |

The holdings entity is created only for account providers that Lunch Flow documents as supporting holdings: Finicity, MX, Pluggy, and SnapTrade.

## Security and privacy

- The API key is stored in the Home Assistant config entry and is never added to entity attributes or logs.
- Requests are sent directly from Home Assistant to `https://lunchflow.app/api/v1` over HTTPS.
- Only when currency conversion is enabled, a separate unauthenticated request fetches public exchange rates from `https://api.frankfurter.dev/v1/latest`. It contains no Lunch Flow API key, account details, balances, or transactions.
- The integration is read-only and does not initiate bank connections, move money, or modify Lunch Flow data.
- Transaction descriptions and merchant names are exposed as entity attributes. Restrict access to your Home Assistant instance accordingly.

## Troubleshooting

### No accounts appear

Open the API destination in Lunch Flow and verify that the desired accounts are enabled in **Account Access**.

### Authentication failed

Home Assistant will start a reauthentication flow. Enter a valid key from the Lunch Flow API destination.

### Holdings are missing

Lunch Flow only provides holdings for supported brokerage providers. A normal bank account will not create a holdings sensor.

## Development

```bash
python -m pip install -r requirements_test.txt
ruff check .
pytest
```

## License

[MIT](LICENSE)
