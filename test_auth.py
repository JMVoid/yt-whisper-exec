#!/usr/bin/env python3
"""
Test script for environment-based StaticTokenVerifier authentication logic.
This script tests the new token-based authentication system from main.py.
"""

import os
import sys
from unittest.mock import patch

# Add the current directory to Python path to import main
sys.path.insert(0, '.')

def test_static_token_auth():
    """Test the StaticTokenVerifier authentication logic."""
    
    # Test 1: No STATIC_TOKENS set (should use default admin token)
    print("Test 1: Using default admin token (no STATIC_TOKENS)")
    with patch.dict(os.environ, {}, clear=True):
        # Import and create the MCP server instance
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import mcp
        
        # The server should be configured with default admin token
        auth_handler = mcp._auth
        if auth_handler and hasattr(auth_handler, 'tokens'):
            print("✓ StaticTokenVerifier configured with default token")
            expected_tokens = ['admin-token']
            actual_tokens = list(auth_handler.tokens.keys())
            if set(expected_tokens).issubset(set(actual_tokens)):
                print("✓ Default admin token is present")
                # Verify token claims
                token_claims = auth_handler.tokens['admin-token']
                expected_client_id = "admin@youtube-summary.com"
                expected_scopes = ["read:data", "write:data", "admin:full"]
                if (token_claims.get('client_id') == expected_client_id and 
                    token_claims.get('scopes') == expected_scopes):
                    print("✓ Default admin token has correct claims")
                else:
                    print(f"✗ Default token claims incorrect. Got: {token_claims}")
            else:
                print(f"✗ Token mismatch. Expected: {expected_tokens}, Got: {actual_tokens}")
        else:
            print("✗ StaticTokenVerifier not properly configured")
    
    # Test 2: STATIC_TOKENS set with custom configuration
    print("\nTest 2: STATIC_TOKENS set with custom admin token")
    custom_tokens_json = '{"my-custom-admin": {"client_id": "custom@admin.com", "scopes": ["read:data", "write:data", "admin:full"]}}'
    with patch.dict(os.environ, {'STATIC_TOKENS': custom_tokens_json}):
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import mcp
        
        auth_handler = mcp._auth
        if auth_handler and hasattr(auth_handler, 'tokens'):
            tokens = auth_handler.tokens
            if 'my-custom-admin' in tokens:
                print("✓ Custom STATIC_TOKENS correctly parsed")
                expected_client_id = "custom@admin.com"
                expected_scopes = ["read:data", "write:data", "admin:full"]
                if (tokens['my-custom-admin']['client_id'] == expected_client_id and
                    tokens['my-custom-admin']['scopes'] == expected_scopes):
                    print("✓ Custom token has correct claims")
                else:
                    print(f"✗ Custom token claims incorrect: {tokens['my-custom-admin']}")
            else:
                print("✗ Custom token not found in static tokens")
        else:
            print("✗ StaticTokenVerifier not properly configured for custom tokens")
    
    # Test 3: Test token validation logic
    print("\nTest 3: Token validation scenarios")
    with patch.dict(os.environ, {}, clear=True):
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import mcp
        
        auth_handler = mcp._auth
        if auth_handler:
            # Test valid admin token
            try:
                result = auth_handler.validate_token("admin-token")
                if result and result.get('client_id') == 'admin@youtube-summary.com':
                    print("✓ Admin token validation successful")
                else:
                    print("✗ Admin token validation failed")
            except Exception as e:
                print(f"✗ Admin token validation error: {e}")
            
            # Test invalid token
            try:
                result = auth_handler.validate_token("invalid-token")
                if result is None:
                    print("✓ Invalid token correctly rejected")
                else:
                    print("✗ Invalid token should have been rejected")
            except Exception as e:
                print(f"✓ Invalid token rejection handled: {e}")
        else:
            print("✗ Could not access auth handler for validation tests")
    
    # Test 4: Invalid JSON in STATIC_TOKENS (should fallback to default)
    print("\nTest 4: Invalid STATIC_TOKENS JSON (should fallback to default)")
    with patch.dict(os.environ, {'STATIC_TOKENS': 'invalid-json-string'}):
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import mcp
        
        auth_handler = mcp._auth
        if auth_handler and hasattr(auth_handler, 'tokens'):
            tokens = auth_handler.tokens
            if 'admin-token' in tokens:
                print("✓ Invalid JSON correctly handled with default fallback")
            else:
                print("✗ Invalid JSON should have triggered default fallback")
        else:
            print("✗ StaticTokenVerifier not properly configured for error handling")

if __name__ == "__main__":
    test_static_token_auth()
