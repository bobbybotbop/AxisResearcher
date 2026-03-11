"""
eBay OAuth Token Management: mint application and user tokens.

Mint application tokens (client credentials) and user tokens (authorization code
or refresh). Updates .env with tokens; values are written without quoting so
special characters (e.g. ^, #) are preserved.

Required environment variables:
- client_id: eBay App client ID
- client_secret: eBay App client secret
- redirect_uri or redirect_url: eBay App RuName (redirect URI)
- refresh_token: (for refresh_user_token only)
"""

import os
import base64
import urllib.parse
import webbrowser
from dotenv import load_dotenv
import requests

load_dotenv()

# Environment variables; redirect supports both keys for template compatibility
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
REDIRECT_URI = os.getenv('redirect_uri') or os.getenv('redirect_url')
REFRESH_TOKEN = os.getenv('refresh_token')

# OAuth endpoints
SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
PRODUCTION_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
PRODUCTION_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Keys we can write via update_env (aligned with env_template)
ENV_TOKEN_KEYS = ('application_token', 'user_token', 'refresh_token', 'auth_code')

# Default scopes for user consent, exchange, and refresh (must match across all three)
# User token is used for: Sell Inventory API, Trading API (UploadSiteHostedPictures)
# Application token (separate) handles: Browse API, Commerce Taxonomy
DEFAULT_USER_SCOPES = [
    "https://api.ebay.com/oauth/api_scope",           # Trading API (image upload), legacy compatibility
    "https://api.ebay.com/oauth/api_scope/sell.inventory",  # Inventory API (create listing, offer, publish, location)
]


def _env_path():
    """Path to project-root .env file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')


def update_env(updates):
    """
    Update .env file by key. Preserves special characters (^, #, =, etc.) by
    writing unquoted values. Updates only the keys present in the dict.

    Args:
        updates: dict of key -> value (e.g. {'application_token': 'v^1.1#...'})
    """
    if not updates:
        return
    allowed = set(ENV_TOKEN_KEYS)
    updates = {k: v for k, v in updates.items() if k in allowed and v is not None}
    if not updates:
        return
    env_path = _env_path()
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    new_lines = []
    found = {k: False for k in updates}
    for line in lines:
        stripped = line.strip()
        replaced = False
        for key, value in updates.items():
            if stripped.startswith(key + '='):
                new_lines.append(f'{key}={value}\n')
                found[key] = True
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    for key, value in updates.items():
        if not found[key]:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'{key}={value}\n')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def mint_application_token(environment="production", scopes=None):
    """
    Mint an application access token via client credentials grant.
    On success, updates .env with application_token.

    Args:
        environment: "production" or "sandbox"
        scopes: list of scope URLs (default: basic api_scope)

    Returns:
        Token response dict with access_token, expires_in, etc., or None on failure.
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("CLIENT_ID and CLIENT_SECRET are required in .env")
    if scopes is None:
        scopes = ["https://api.ebay.com/oauth/api_scope"]
    token_url = PRODUCTION_TOKEN_URL if environment.lower() == "production" else SANDBOX_TOKEN_URL
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_bytes}'
    }
    scope_str = ' '.join(scopes)
    data = {'grant_type': 'client_credentials', 'scope': scope_str}
    try:
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            if access_token:
                update_env({'application_token': access_token})
            return token_data
        print(f"Application token mint failed: {response.status_code} - {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error minting application token: {e}")
        return None


def get_user_consent_url(environment="production", scopes=None, state=None, prompt=None):
    """
    Build the user consent URL for the authorization code flow.

    Args:
        environment: "production" or "sandbox"
        scopes: list of OAuth scope URLs
        state: optional state for CSRF
        prompt: optional (e.g. "login")

    Returns:
        Full consent URL string.

    Raises:
        ValueError: if client_id or redirect URI missing.
    """
    if not CLIENT_ID:
        raise ValueError("CLIENT_ID is required in .env")
    if not REDIRECT_URI:
        raise ValueError("redirect_uri or redirect_url is required in .env")
    if scopes is None:
        scopes = DEFAULT_USER_SCOPES
    auth_url = PRODUCTION_AUTH_URL if environment.lower() == "production" else SANDBOX_AUTH_URL
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes)
    }
    if state:
        params['state'] = state
    if prompt:
        params['prompt'] = prompt
    query_string = urllib.parse.urlencode(params)
    return f"{auth_url}?{query_string}"


def open_user_consent_page(environment="production", scopes=None, state=None, prompt=None):
    """Build consent URL and open it in the default browser. Returns the URL."""
    url = get_user_consent_url(environment, scopes, state, prompt)
    webbrowser.open(url)
    return url


def exchange_code_for_user_token(authorization_code, environment="production", scopes=None):
    """
    Exchange authorization code for user access token and refresh token.
    On success, updates .env with user_token, refresh_token, and auth_code.

    Args:
        authorization_code: code from consent redirect
        environment: "production" or "sandbox"
        scopes: list of scopes (must match consent request)

    Returns:
        Token response dict or None on failure.
    """
    if not authorization_code:
        raise ValueError("authorization_code is required")
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("CLIENT_ID and CLIENT_SECRET are required in .env")
    if not REDIRECT_URI:
        raise ValueError("redirect_uri or redirect_url is required in .env")
    if scopes is None:
        scopes = DEFAULT_USER_SCOPES
    token_url = PRODUCTION_TOKEN_URL if environment.lower() == "production" else SANDBOX_TOKEN_URL
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_bytes}'
    }
    decoded_code = urllib.parse.unquote(authorization_code)
    data = {
        'grant_type': 'authorization_code',
        'code': decoded_code,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(scopes)
    }
    try:
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            updates = {'user_token': access_token}
            if refresh_token:
                updates['refresh_token'] = refresh_token
            updates['auth_code'] = authorization_code
            update_env(updates)
            return token_data
        print(f"Exchange code failed: {response.status_code} - {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error exchanging code: {e}")
        return None


def refresh_user_token(environment="production", scopes=None):
    """
    Refresh user access token using refresh_token from .env.
    On success, updates .env with user_token (and refresh_token if returned).

    Args:
        environment: "production" or "sandbox"
        scopes: list of scopes (same as original consent)

    Returns:
        Token response dict or None on failure.

    Raises:
        ValueError: if refresh_token or credentials missing.
    """
    if not REFRESH_TOKEN:
        raise ValueError("refresh_token is required in .env")
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("CLIENT_ID and CLIENT_SECRET are required in .env")
    if scopes is None:
        scopes = DEFAULT_USER_SCOPES
    token_url = PRODUCTION_TOKEN_URL if environment.lower() == "production" else SANDBOX_TOKEN_URL
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_bytes}'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'scope': ' '.join(scopes)
    }
    try:
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            new_refresh = token_data.get('refresh_token', REFRESH_TOKEN)
            updates = {'user_token': access_token}
            if new_refresh:
                updates['refresh_token'] = new_refresh
            update_env(updates)
            return token_data
        print(f"Refresh user token failed: {response.status_code} - {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error refreshing user token: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python refreshTokenTest.py <command> [args...]")
        print("Commands (default environment: production):")
        print("  mint-app [production|sandbox]")
        print("  consent [production|sandbox]")
        print("  open-consent [production|sandbox]")
        print("  exchange <code> [production|sandbox]")
        print("  refresh-user [production|sandbox]")
        sys.exit(1)
    command = sys.argv[1].lower()
    env_arg = None
    if command == "exchange":
        if len(sys.argv) < 3:
            print("Usage: exchange <auth_code> [production|sandbox]")
            sys.exit(1)
        code = sys.argv[2]
        env_arg = sys.argv[3] if len(sys.argv) > 3 else "production"
    else:
        env_arg = sys.argv[2] if len(sys.argv) > 2 else "production"
    env = env_arg if env_arg in ("production", "sandbox") else "production"
    try:
        if command == "mint-app":
            result = mint_application_token(environment=env)
            if result:
                print("Application token minted and saved to .env")
        elif command == "consent":
            url = get_user_consent_url(environment=env)
            print(url)
        elif command == "open-consent":
            url = open_user_consent_page(environment=env)
            print("Opened:", url)
        elif command == "exchange":
            result = exchange_code_for_user_token(code, environment=env)
            if result:
                print("User token and refresh_token saved to .env")
        elif command == "refresh-user":
            result = refresh_user_token(environment=env)
            if result:
                print("User token updated in .env")
        else:
            print("Unknown command. Use mint-app, consent, open-consent, exchange, or refresh-user.")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
