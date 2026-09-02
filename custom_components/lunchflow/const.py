"""Constants for the Lunch Flow integration."""

from datetime import timedelta

DOMAIN = "lunchflow"

CONF_API_KEY = "api_key"
CONF_INCLUDE_PENDING = "include_pending"
CONF_TRANSACTION_DAYS = "transaction_days"
CONF_UPDATE_INTERVAL = "update_interval"

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
