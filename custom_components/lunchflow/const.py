"""Constants for the Lunch Flow integration."""

from datetime import timedelta

DOMAIN = "lunchflow"

CONF_API_KEY = "api_key"
CONF_INCLUDE_PENDING = "include_pending"
CONF_TRANSACTION_DAYS = "transaction_days"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TARGET_CURRENCY = "target_currency"
DEFAULT_TARGET_CURRENCY = "original"

CURRENCY_OPTIONS = {
    DEFAULT_TARGET_CURRENCY: "Disabled (original currencies only)",
    "CAD": "CAD - Canadian dollar",
    "EUR": "EUR - Euro",
    "USD": "USD - US dollar",
    "AUD": "AUD - Australian dollar",
    "BRL": "BRL - Brazilian real",
    "CHF": "CHF - Swiss franc",
    "CNY": "CNY - Chinese yuan",
    "CZK": "CZK - Czech koruna",
    "DKK": "DKK - Danish krone",
    "GBP": "GBP - Pound sterling",
    "HKD": "HKD - Hong Kong dollar",
    "HUF": "HUF - Hungarian forint",
    "IDR": "IDR - Indonesian rupiah",
    "ILS": "ILS - Israeli shekel",
    "INR": "INR - Indian rupee",
    "ISK": "ISK - Icelandic krona",
    "JPY": "JPY - Japanese yen",
    "KRW": "KRW - South Korean won",
    "MXN": "MXN - Mexican peso",
    "MYR": "MYR - Malaysian ringgit",
    "NOK": "NOK - Norwegian krone",
    "NZD": "NZD - New Zealand dollar",
    "PHP": "PHP - Philippine peso",
    "PLN": "PLN - Polish zloty",
    "RON": "RON - Romanian leu",
    "SEK": "SEK - Swedish krona",
    "SGD": "SGD - Singapore dollar",
    "THB": "THB - Thai baht",
    "TRY": "TRY - Turkish lira",
    "ZAR": "ZAR - South African rand",
}

DEFAULT_INCLUDE_PENDING = True
DEFAULT_TRANSACTION_DAYS = 30
DEFAULT_UPDATE_INTERVAL = 30
MIN_TRANSACTION_DAYS = 1
MAX_TRANSACTION_DAYS = 365
MIN_UPDATE_INTERVAL = 5
MAX_UPDATE_INTERVAL = 1440

DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
LUNCHFLOW_API_URL = "https://lunchflow.app/api/v1"
LUNCHFLOW_URL = "https://lunchflow.app"

PLATFORMS = ["sensor"]

SUPPORTED_HOLDINGS_PROVIDERS = {"finicity", "mx", "pluggy", "snaptrade"}
