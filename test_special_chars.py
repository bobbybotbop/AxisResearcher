#!/usr/bin/env python3
"""
Test script to demonstrate handling of special characters in command line arguments
"""

import sys

def test_arguments():
    """Test how arguments are received"""
    print("🔍 Testing special character handling...")
    print(f"Command: {sys.argv[1] if len(sys.argv) > 1 else 'None'}")
    print(f"Arguments received: {len(sys.argv) - 2}")
    
    for i, arg in enumerate(sys.argv[2:], 1):
        print(f"  Arg {i}: '{arg}'")
    
    print("\n✅ Special characters preserved!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_special_chars.py <command> [args...]")
        print("Try: python test_special_chars.py search \"item with ^ and | characters\"")
        sys.exit(1)
    
    test_arguments()
