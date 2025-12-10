"""
eBay OAuth Token Management Functions

This module provides functions for eBay OAuth user consent and token refresh operations.
Based on eBay OAuth documentation:
- https://developer.ebay.com/api-docs/static/oauth-consent-request.html
- https://developer.ebay.com/api-docs/static/oauth-refresh-token-request.html

Required environment variables:
- client_id: Your eBay App client ID
- client_secret: Your eBay App client secret
- redirect_uri: Your eBay App RuName (redirect URI)
- refresh_token: Your eBay refresh token (for refresh function)
"""

import os
import base64
import urllib.parse
import webbrowser
from dotenv import load_dotenv, set_key
import requests
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Environment variables
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
REDIRECT_URI = os.getenv('redirect_uri')  # This should be your RuName
REFRESH_TOKEN = os.getenv('refresh_token')

# OAuth endpoints
SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
PRODUCTION_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
PRODUCTION_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"


def create_user_consent_url(environment="sandbox", scopes=None, state=None, locale=None, prompt=None):
    """
    Create a user consent URL for eBay OAuth authorization code grant flow.
    
    This function generates the URL that users need to visit to grant consent
    for your application to access their eBay account data.
    
    Args:
        environment (str): "sandbox" or "production"
        scopes (list): List of OAuth scopes (default: common eBay scopes)
        state (str): Optional state parameter for CSRF protection
        locale (str): Optional locale for consent page (e.g., "en-US", "de-DE")
        prompt (str): Optional prompt parameter ("login" to force login)
    
    Returns:
        str: Complete consent URL for user to visit
    
    Raises:
        ValueError: If required parameters are missing
    """
    if not CLIENT_ID:
        raise ValueError("❌ CLIENT_ID not found in environment variables")
    
    if not REDIRECT_URI:
        raise ValueError("❌ REDIRECT_URI not found in environment variables")
    
    # Default scopes - using only the basic scope that's available
    if scopes is None:
        scopes = [
            "https://api.ebay.com/oauth/api_scope"  # Basic API access scope - only one available
        ]
    
    # Choose endpoint based on environment
    if environment.lower() == "production":
        auth_url = PRODUCTION_AUTH_URL
        print("🌐 Using PRODUCTION environment")
    else:
        auth_url = SANDBOX_AUTH_URL
        print("🧪 Using SANDBOX environment")
    
    # Build query parameters
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes)
    }
    
    # Add optional parameters
    if state:
        params['state'] = state
    if locale:
        params['locale'] = locale
    if prompt:
        params['prompt'] = prompt
    
    # Create the complete URL
    query_string = urllib.parse.urlencode(params)
    consent_url = f"{auth_url}?{query_string}"
    
    print(f"✅ Generated consent URL:")
    print(f"🔗 {consent_url}")
    print(f"\n📋 Parameters:")
    print(f"  Client ID: {CLIENT_ID[:10]}...")
    print(f"  Redirect URI: {REDIRECT_URI}")
    print(f"  Scopes: {len(scopes)} scopes")
    print(f"  State: {state if state else 'Not provided'}")
    
    return consent_url


def open_user_consent_page(environment="sandbox", scopes=None, state=None, locale=None, prompt=None):
    """
    Create and open the user consent page in the default web browser.
    
    Args:
        environment (str): "sandbox" or "production"
        scopes (list): List of OAuth scopes
        state (str): Optional state parameter for CSRF protection
        locale (str): Optional locale for consent page
        prompt (str): Optional prompt parameter
    
    Returns:
        str: The consent URL that was opened
    """
    try:
        consent_url = create_user_consent_url(environment, scopes, state, locale, prompt)
        
        print(f"\n🌐 Opening consent page in browser...")
        webbrowser.open(consent_url)
        
        print(f"\n📝 Instructions:")
        print(f"1. Complete the consent process in your browser")
        print(f"2. Copy the authorization code from the redirect URL")
        print(f"3. Use exchange_authorization_code() to get access tokens")
        
        return consent_url
        
    except Exception as e:
        print(f"❌ Error opening consent page: {e}")
        return None


def exchange_authorization_code(authorization_code, environment="sandbox", scopes=None):
    """
    Exchange authorization code for access token and refresh token.
    
    Args:
        authorization_code (str): The authorization code from consent redirect
        environment (str): "sandbox" or "production"
        scopes (list): List of OAuth scopes (should match consent request)
    
    Returns:
        dict: Token response with access_token, refresh_token, expires_in, etc.
    
    Raises:
        ValueError: If required parameters are missing
    """
    if not authorization_code:
        raise ValueError("❌ Authorization code is required")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("❌ CLIENT_ID and CLIENT_SECRET are required")
    
    if not REDIRECT_URI:
        raise ValueError("❌ REDIRECT_URI is required")
    
    # Default scopes - using only the basic scope that's available
    if scopes is None:
        scopes = [
            "https://api.ebay.com/oauth/api_scope"  # Basic API access scope - only one available
        ]
    
    # Choose endpoint based on environment
    if environment.lower() == "production":
        token_url = PRODUCTION_TOKEN_URL
        print("🌐 Using PRODUCTION environment")
    else:
        token_url = SANDBOX_TOKEN_URL
        print("🧪 Using SANDBOX environment")
    
    # Create Basic Auth header
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    
    # Request headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_bytes}'
    }
    
    # Request payload
    # URL decode the authorization code before sending
    decoded_code = urllib.parse.unquote(authorization_code)
    data = {
        'grant_type': 'authorization_code',
        'code': decoded_code,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(scopes)
    }
    
    try:
        print(f"🔄 Exchanging authorization code for tokens...")
        print(f"🔍 Debug - Client ID: {CLIENT_ID[:10]}...")
        print(f"🔍 Debug - Redirect URI: {REDIRECT_URI}")
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 7200)
            token_type = token_data.get('token_type', 'User Access Token')
            
            print(f"✅ Token exchange successful!")
            print(f"  Token Type: {token_type}")
            print(f"  Expires In: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            print(f"  Access Token: {access_token[:20]}...")
            print(f"  Refresh Token: {refresh_token[:20]}...")
            
            # Save tokens to .env file
            try:
                set_key('.env', 'application_token', access_token)
                if refresh_token:
                    set_key('.env', 'refresh_token', refresh_token)
                print(f"💾 Tokens saved to .env file")
            except Exception as e:
                print(f"⚠️ Warning: Could not save tokens to .env file: {e}")
            
            return token_data
            
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Handle specific error cases
            if response.status_code == 400:
                print("💡 This might be due to:")
                print("   - Invalid authorization code")
                print("   - Authorization code expired")
                print("   - Invalid client credentials")
                print("   - Mismatched redirect URI")
            elif response.status_code == 401:
                print("💡 This might be due to:")
                print("   - Invalid client_id or client_secret")
                print("   - Malformed Basic Auth header")
            
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during token exchange: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error during token exchange: {e}")
        return None


def refresh_application_token(environment="sandbox", scopes=None):
    """
    Refresh user access token using refresh token.
    
    Args:
        environment (str): "sandbox" or "production"
        scopes (list): List of OAuth scopes (should match original consent)
    
    Returns:
        dict: Token response with new access_token, expires_in, etc.
    
    Raises:
        ValueError: If required parameters are missing
    """
    if not REFRESH_TOKEN:
        raise ValueError("❌ REFRESH_TOKEN not found in environment variables")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("❌ CLIENT_ID and CLIENT_SECRET are required")
    
    # Default scopes - using only the basic scope that's available
    if scopes is None:
        scopes = [
            "https://api.ebay.com/oauth/api_scope"  # Basic API access scope - only one available
        ]
    
    # Choose endpoint based on environment
    if environment.lower() == "production":
        token_url = PRODUCTION_TOKEN_URL
        print("🌐 Using PRODUCTION environment")
    else:
        token_url = SANDBOX_TOKEN_URL
        print("🧪 Using SANDBOX environment")
    
    # Create Basic Auth header
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    
    # Request headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_bytes}'
    }
    
    # Request payload
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'scope': ' '.join(scopes)
    }
    
    try:
        print(f"🔄 Refreshing user access token...")
        print(f"🔍 Debug - Client ID: {CLIENT_ID[:10]}...")
        print(f"🔍 Debug - Refresh Token: {REFRESH_TOKEN[:20]}...")
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', REFRESH_TOKEN)
            expires_in = token_data.get('expires_in', 7200)
            token_type = token_data.get('token_type', 'User Access Token')
            
            print(f"✅ Token refresh successful!")
            print(f"  Token Type: {token_type}")
            print(f"  Expires In: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            print(f"  New Access Token: {access_token[:20]}...")
            
            if new_refresh_token != REFRESH_TOKEN:
                print(f"  New Refresh Token: {new_refresh_token[:20]}...")
            
            # Save tokens to .env file
            try:
                set_key('.env', 'application_token', access_token)
                if new_refresh_token != REFRESH_TOKEN:
                    set_key('.env', 'refresh_token', new_refresh_token)
                print(f"💾 Tokens updated in .env file")
            except Exception as e:
                print(f"⚠️ Warning: Could not save tokens to .env file: {e}")
            
            return token_data
            
        else:
            print(f"❌ Token refresh failed: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Handle specific error cases
            if response.status_code == 400:
                print("💡 This might be due to:")
                print("   - Invalid refresh token")
                print("   - Refresh token expired")
                print("   - Invalid client credentials")
                print("   - User changed password or revoked access")
            elif response.status_code == 401:
                print("💡 This might be due to:")
                print("   - Invalid client_id or client_secret")
                print("   - Malformed Basic Auth header")
            
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error refreshing token: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error refreshing token: {e}")
        return None


def complete_oauth_flow(environment="sandbox", scopes=None, state=None, locale=None):
    """
    Complete the full OAuth flow: consent + token exchange.
    
    This function will:
    1. Generate and open the consent URL
    2. Wait for user to provide authorization code
    3. Exchange the code for tokens
    
    Args:
        environment (str): "sandbox" or "production"
        scopes (list): List of OAuth scopes
        state (str): Optional state parameter
        locale (str): Optional locale
    
    Returns:
        dict: Token response if successful, None if failed
    """
    try:
        print(f"🚀 Starting complete OAuth flow...")
        
        # Step 1: Open consent page
        consent_url = open_user_consent_page(environment, scopes, state, locale)
        if not consent_url:
            return None
        
        # Step 2: Get authorization code from user
        print(f"\n⏳ Please complete the consent process and copy the authorization code from the redirect URL.")
        print(f"💡 Look for the 'code' parameter in the URL after you're redirected.")
        
        authorization_code = input("\n📝 Enter the authorization code: ").strip()
        
        if not authorization_code:
            print("❌ No authorization code provided")
            return None
        
        # Step 3: Exchange code for tokens
        print(f"\n🔄 Exchanging authorization code for tokens...")
        token_response = exchange_authorization_code(authorization_code, environment, scopes)
        
        if token_response:
            print(f"\n🎉 OAuth flow completed successfully!")
            return token_response
        else:
            print(f"\n❌ OAuth flow failed during token exchange")
            return None
            
    except KeyboardInterrupt:
        print(f"\n⚠️ OAuth flow cancelled by user")
        return None
    except Exception as e:
        print(f"❌ Error in OAuth flow: {e}")
        return None


def test_functions():
    """
    Test function to demonstrate usage of OAuth functions.
    """
    print("🧪 Testing eBay OAuth Functions")
    print("=" * 50)
    
    # Test 1: Create consent URL
    print("\n1️⃣ Testing consent URL creation...")
    try:
        consent_url = create_user_consent_url(
            environment="sandbox",
            scopes=[
                "https://api.ebay.com/oauth/api_scope"  # Only use the basic scope that's available
            ],
            state="test_state_123"
        )
        print("✅ Consent URL created successfully")
    except Exception as e:
        print(f"❌ Error creating consent URL: {e}")
    
    # Test 2: Refresh token (if available)
    print("\n2️⃣ Testing token refresh...")
    try:
        if REFRESH_TOKEN:
            token_response = refresh_application_token(environment="sandbox")
            if token_response:
                print("✅ Token refresh successful")
            else:
                print("❌ Token refresh failed")
        else:
            print("⚠️ No refresh token available for testing")
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
    
    print("\n🎯 Test completed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("❌ Usage: python refreshTokenTest.py <command> [args...]")
        print("Commands:")
        print("  consent [sandbox|production] - Create consent URL")
        print("  open [sandbox|production] - Open consent page in browser")
        print("  exchange <auth_code> [sandbox|production] - Exchange auth code for tokens")
        print("  refresh [sandbox|production] - Refresh access token")
        print("  flow [sandbox|production] - Complete OAuth flow")
        print("  test - Run test functions")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "consent":
            env = sys.argv[2] if len(sys.argv) > 2 else "sandbox"
            create_user_consent_url(environment=env)
            
        elif command == "open":
            env = sys.argv[2] if len(sys.argv) > 2 else "sandbox"
            open_user_consent_page(environment=env)
            
        elif command == "exchange":
            if len(sys.argv) < 3:
                print("❌ Usage: exchange <auth_code> [sandbox|production]")
                sys.exit(1)
            auth_code = sys.argv[2]
            env = sys.argv[3] if len(sys.argv) > 3 else "sandbox"
            exchange_authorization_code(auth_code, environment=env)
            
        elif command == "refresh":
            env = sys.argv[2] if len(sys.argv) > 2 else "sandbox"
            refresh_application_token(environment=env)
            
        elif command == "flow":
            env = sys.argv[2] if len(sys.argv) > 2 else "sandbox"
            complete_oauth_flow(environment=env)
            
        elif command == "test":
            test_functions()
            
        else:
            print("❌ Unknown command. Use 'python refreshTokenTest.py' to see available commands.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
