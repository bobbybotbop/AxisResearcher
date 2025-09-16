"""
Test URL decoding of authorization code
"""
import urllib.parse

# Your authorization code
auth_code = "v%5E1.1%23i%5E1%23f%5E0%23p%5E3%23I%5E3%23r%5E1%23t%5EUl41Xzk6N0E1RkJFNUI5MUI5RERFNjRCMkNDQzI4OUQwNkEzMTJfMV8xI0VeMjYw"

print("🔍 AUTHORIZATION CODE ANALYSIS")
print("=" * 50)

print(f"Original (URL encoded): {auth_code}")

# Decode it
decoded = urllib.parse.unquote(auth_code)
print(f"Decoded: {decoded}")

print(f"\nLength: {len(auth_code)} characters")
print(f"Contains % symbols: {'%' in auth_code}")
print(f"Contains # symbols: {'#' in decoded}")

# Test both versions
print(f"\n🧪 TESTING BOTH VERSIONS:")
print(f"1. URL Encoded: {auth_code}")
print(f"2. URL Decoded: {decoded}")

# Check if it looks like a valid eBay auth code
print(f"\n✅ VALIDATION:")
print(f"Starts with 'v': {auth_code.startswith('v')}")
print(f"Contains version pattern: {'1.1' in decoded}")
print(f"Contains eBay pattern: {'Ul41X' in decoded}")
