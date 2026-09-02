# Lunch Flow for Home Assistant

[![Validate](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/validate.yml)
[![Tests](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/raccommode/lunchflow-home-assistant/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

A read-only Home Assistant custom integration for your [Lunch Flow](https://lunchflow.app) bank accounts. It uses the Lunch Flow Personal REST API and creates account balance, transaction, and supported investment-holdings sensors.

This project is an independent community integration and is not affiliated with or endorsed by Lunch Flow.

## Features

- UI setup with a Lunch Flow Personal API key
- One Home Assistant device per bank account
- Current balance sensor with the account currency
- Recent transaction count sensor
- Latest transaction amount with merchant, description, date, ID, and pending status as attributes
- Total investment holdings value for supported providers
- Configurable polling interval, transaction history range, and pending-transaction inclusion
- Automatic reauthentication flow if Lunch Flow rejects the saved key
- No write operations: the integration only calls `GET` endpoints

## Requirements

- Home Assistant 2025.2.0 or newer
- A Lunch Flow account with connected bank accounts
- A Lunch Flow API destination and Personal API key

In Lunch Flow, go to **Destinations → Add Destination → API**. Copy the generated API key and use the destination's Account Access settings to choose which accounts Home Assistant may read.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/raccommode/lunchflow-home-assistant` as an **Integration** repository.
4. Search for **Lunch Flow** and install it.
5. Restart Home Assistant.

## Manual installation

1. Copy `custom_components/lunchflow` into the `custom_components` directory in your Home Assistant configuration directory.
2. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings → Devices & services**.
2. Select **Add Integration**.
3. Search for **Lunch Flow**.
4. Paste the Personal API key from your Lunch Flow API destination.

Only one Lunch Flow config entry is needed. Every account exposed by the API destination is discovered automatically.

### Options

Open the Lunch Flow integration and select **Configure** to change:

| Option | Default | Range | Description |
| --- | ---: | ---: | --- |
| Update interval | 30 minutes | 5–1440 | How often Home Assistant polls Lunch Flow. |
| Transaction history | 30 days | 1–365 | Date range used for transaction sensors. |
| Include pending transactions | Enabled | — | Includes unposted transactions returned by Lunch Flow. |

Changing an option reloads the integration automatically.

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
