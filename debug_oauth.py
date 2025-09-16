"""
Debug script to help identify OAuth token exchange issues
"""
import os
import base64
import urllib.parse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
REDIRECT_URI = os.getenv('redirect_uri')

def debug_token_exchange(authorization_code):
    """
    Debug the token exchange process with detailed logging
    """
    print("🔍 DEBUGGING TOKEN EXCHANGE")
    print("=" * 50)
    
    # Check environment variables
    print(f"✅ CLIENT_ID: {CLIENT_ID}")
    print(f"✅ CLIENT_SECRET: {'SET' if CLIENT_SECRET else 'NOT SET'}")
    print(f"✅ REDIRECT_URI: {REDIRECT_URI}")
    
    # Production token endpoint
    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    
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
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'https://api.ebay.com/oauth/api_scope'
    }
    
    print(f"\n🔍 REQUEST DETAILS:")
    print(f"URL: {token_url}")
    print(f"Headers: {headers}")
    print(f"Data: {data}")
    print(f"Auth String: {auth_string}")
    print(f"Auth Bytes: {auth_bytes}")
    
    try:
        print(f"\n🔄 Making token exchange request...")
        response = requests.post(token_url, headers=headers, data=data)
        
        print(f"\n📊 RESPONSE:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Access Token: {token_data.get('access_token', 'N/A')[:20]}...")
            print(f"Refresh Token: {token_data.get('refresh_token', 'N/A')[:20]}...")
            print(f"Expires In: {token_data.get('expires_in', 'N/A')}")
        else:
            print(f"\n❌ FAILED!")
            print(f"Error: {response.status_code}")
            
            # Try to parse error response
            try:
                error_data = response.json()
                print(f"Error Details: {error_data}")
            except:
                print(f"Raw Error: {response.text}")
                
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_oauth.py <authorization_code>")
        sys.exit(1)
    
    auth_code = sys.argv[1]
    debug_token_exchange(auth_code)
