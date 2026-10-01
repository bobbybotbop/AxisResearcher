AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_INVENTORY_API_BASE = "https://api.ebay.com/sell/inventory/v1"
EBAY_TRADING_API_URL = "https://api.ebay.com/ws/api.dll"
EBAY_BROWSE_API_BASE = "https://api.ebay.com/buy/browse/v1"
EBAY_MARKETPLACE_ID = "EBAY_US"

TRADING_API_SITE_ID = "0"
TRADING_API_COMPATIBILITY_LEVEL = "967"

DEFAULT_USER_SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.marketing",
]

ENV_TOKEN_KEYS = ("application_token", "user_token", "refresh_token", "auth_code")
