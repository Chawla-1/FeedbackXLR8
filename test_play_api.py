"""
Direct GET test for Google Play Developer API (Android Publisher v3).
Endpoint: GET https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{packageName}/reviews
"""
import os
import sys
import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

sys.stdout.reconfigure(encoding="utf-8")

# Configuration
KEY_FILE = os.path.join(os.path.dirname(__file__), "animelot-d4b0d8fae594.json")
PACKAGE_NAME = "com.xvoid.vault"

print(f"=== Testing Google Play Reviews API for '{PACKAGE_NAME}' ===")
print(f"Using Service Account Key: {KEY_FILE}\n")

# 1. Generate OAuth2 Bearer Access Token
try:
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/androidpublisher"]
    )
    creds.refresh(Request())
    access_token = creds.token
    print(f"✅ Access Token Generated (starts with: {access_token[:20]}...)")
except Exception as e:
    print(f"❌ Failed to generate access token: {e}")
    exit(1)

# 2. Make Direct HTTP GET Request
url = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/reviews"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
}

print(f"\n📡 Sending GET request to:\n   {url}")
response = requests.get(url, headers=headers)

print(f"\n📥 HTTP Status Code: {response.status_code}")
print("Response Headers:")
for k in ["content-type", "date", "www-authenticate"]:
    if k in response.headers:
        print(f"   {k}: {response.headers[k]}")

print("\nResponse Body:")
try:
    parsed = response.json()
    print(json.dumps(parsed, indent=2))
except Exception:
    print(response.text)
