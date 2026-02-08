#!/usr/bin/env python3
"""
Test script for ImprovMX webhook endpoint
This script simulates an incoming email from ImprovMX
"""

import requests
import json
from datetime import datetime

# Webhook endpoint URL
WEBHOOK_URL = "http://localhost:42010/webhook"

# Sample email data matching ImprovMX format
sample_email = {
    "headers": {
        "X-Forwarding-Service": "ImprovMX v3.0.0",
        "Received-SPF": [
            "pass (improvmx.com: domain of example.com designates xxx.xxx.xxx.xxx as permitted sender) receiver=mx1.improvmx.com; client-ip=xxx.xxx.xxx.xxx; helo=example.com;"
        ],
        "Delivered-To": "test@puntoa.ar",
        "DKIM-Signature": [
            "v=1; a=rsa-sha256; c=relaxed/relaxed; d=improvmx.com; i=@improvmx.com; q=dns/txt; s=20191126; t=1581630208; h=date : from : to : subject : content-type : message-id; bh=XXX=; b=XXX=="
        ],
        "Authentication-Results": [
            "mx1.improvmx.com; spf=pass (improvmx.com: domain of example.com designates xxx.xxx.xxx.xxx as permitted sender) smtp.mailfrom=example.com; dkim=none"
        ]
    },
    "to": [
        {
            "name": "Test User",
            "email": "test@puntoa.ar"
        }
    ],
    "from": {
        "name": "Email Test",
        "email": "test@example.com"
    },
    "subject": "This is a test email from ImprovMX",
    "message-id": "test-message-id@example.com",
    "date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S -0000"),
    "return-path": {
        "name": None,
        "email": "test@example.com"
    },
    "timestamp": int(datetime.utcnow().timestamp()),
    "text": "Sample text in the email's body as the text/plain value.",
    "html": "<p>Sample text in the email's body as the text/html value.</p>",
    "inlines": [
        {
            "type": "image/png",
            "name": "screenshot.png",
            "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "cid": "some_random_id"
        }
    ],
    "attachments": [
        {
            "type": "text/plain",
            "name": "test.txt",
            "content": "VGVzdCBhdHRhY2htZW50IGNvbnRlbnQ=",
            "encoding": "binary"
        }
    ]
}

def test_webhook():
    """Test the webhook endpoint"""
    print("=" * 60)
    print("Testing ImprovMX Webhook")
    print("=" * 60)
    
    # Test 1: Send sample email
    print("\n1. Sending sample email...")
    try:
        response = requests.post(WEBHOOK_URL, json=sample_email, timeout=10)
        
        if response.status_code == 200:
            print("✓ Email sent successfully")
            print(f"  Response: {response.json()}")
            email_id = response.json().get('email_id')
        else:
            print(f"✗ Failed with status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed. Make sure the server is running on port 42010")
        return
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return
    
    # Test 2: Check health endpoint
    print("\n2. Checking health endpoint...")
    try:
        response = requests.get("http://localhost:42010/", timeout=5)
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Test 3: Retrieve emails
    print("\n3. Retrieving emails...")
    try:
        response = requests.get("http://localhost:42010/emails?limit=5", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved {data['count']} emails")
            for i, email in enumerate(data['emails'], 1):
                print(f"  {i}. From: {email['from']['email']} | Subject: {email['subject']}")
        else:
            print(f"✗ Failed to retrieve emails: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Test 4: Get specific email
    if email_id:
        print(f"\n4. Retrieving specific email (ID: {email_id})...")
        try:
            response = requests.get(f"http://localhost:42010/emails/{email_id}", timeout=5)
            if response.status_code == 200:
                print("✓ Email retrieved successfully")
                email_data = response.json()['email']
                print(f"  Subject: {email_data['subject']}")
                print(f"  From: {email_data['from']['email']}")
                print(f"  To: {[t['email'] for t in email_data['to']]}")
                print(f"  Attachments: {len(email_data.get('attachments', []))}")
                print(f"  Inlines: {len(email_data.get('inlines', []))}")
            else:
                print(f"✗ Failed to retrieve email: {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_webhook()