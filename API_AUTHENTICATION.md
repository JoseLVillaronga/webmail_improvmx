# API Authentication, Rate Limiting & Security Documentation

## Overview

This document describes authentication, rate limiting, and brute force protection mechanisms for ImprovMX Webhook API.

## Security Features

The API implements multiple layers of protection:

1. **Bearer Token Authentication** - Required for protected endpoints
2. **Rate Limiting** - Prevents abuse and ensures fair usage
3. **Brute Force Protection** - Blocks IPs with multiple failed authentication attempts

## Authentication Method

The API uses **Bearer Token Authentication** for all endpoints except `/webhook` and `/docs`.

### Required Headers

All protected endpoints require the following HTTP header:

```
Authorization: Bearer YOUR_API_KEY
```

Where `YOUR_API_KEY` is the value of `API_KEY` environment variable (256-bit token).

## Endpoints

### Public Endpoints (No Authentication Required)

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET | `/docs` | API Documentation (Markdown format) |
| POST | `/webhook` | Receives emails from ImprovMX |

### Protected Endpoints (Require Authentication)

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET | `/` | Health check endpoint |
| GET | `/emails` | Retrieve stored emails from MongoDB |
| GET | `/emails/<email_id>` | Retrieve a specific email by ID |
| GET | `/emails/<email_id>/attachment/<attachment_name>` | Retrieve a specific attachment from an email |

## Rate Limiting

All endpoints are protected by rate limiting to prevent abuse and ensure fair usage.

### Rate Limits by Endpoint

| Endpoint | Rate Limit | Description |
|----------|-------------|-------------|
| `/` (Health check) | 30 requests/minute | Health checks can be called frequently |
| `/docs` | 60 requests/minute | Documentation access |
| `/webhook` | 200 requests/minute | High limit for email reception |
| `/emails` | 20 requests/minute | Standard rate for listing emails |
| `/emails/<email_id>` | 30 requests/minute | Slightly higher for viewing individual emails |
| `/emails/<email_id>/attachment/<attachment_name>` | 10 requests/minute | Lower limit for downloads (resource intensive) |

### Rate Limit Response

When a rate limit is exceeded:

```json
{
  "error": "Rate limit exceeded: 30 per 1 minute"
}
```

**HTTP Status Code:** 429 Too Many Requests

### Global Limits

In addition to per-endpoint limits, there are global limits:
- 200 requests per day
- 50 requests per hour

These apply to all endpoints combined per IP address.

## Brute Force Protection

The API includes protection against brute force attacks on authentication.

### Protection Rules

- **Maximum Failed Attempts:** 5 failed authentication attempts
- **Time Window:** Attempts are counted within a 5-minute window
- **Block Duration:** IP is blocked for 15 minutes after exceeding limit
- **Automatic Cleanup:** Old attempts are automatically removed from tracking

### How It Works

1. Each failed authentication attempt is tracked per IP address
2. After 5 failed attempts within 5 minutes, the IP is blocked
3. Blocked IPs receive a 429 status with remaining block time
4. Successful authentication clears all failed attempts for that IP
5. Old attempts outside 5-minute window are automatically removed

### Brute Force Protection Response

When an IP is blocked:

```json
{
  "success": false,
  "error": "Too many failed attempts. Please try again later."
}
```

**HTTP Status Code:** 429 Too Many Requests

### Example Scenario

```
User IP: 192.168.1.100

1. 10:00 - Invalid API key (Attempt 1/5)
2. 10:01 - Invalid API key (Attempt 2/5)
3. 10:02 - Invalid API key (Attempt 3/5)
4. 10:03 - Invalid API key (Attempt 4/5)
5. 10:04 - Invalid API key (Attempt 5/5) → IP BLOCKED for 15 minutes
6. 10:05 - Any request → Returns 429 with error message
7. 10:20 - Block expires → IP can try again
```

## Authentication Flow

### Success Response

When a valid API key is provided, the request proceeds normally:

```json
{
  "success": true,
  "data": { ... }
}
```

### Error Responses

#### 1. Missing Authorization Header (HTTP 401)

```json
{
  "success": false,
  "error": "Missing Authorization header"
}
```

**Solution:** Include `Authorization` header with your Bearer token.

#### 2. Invalid Authorization Header Format (HTTP 401)

```json
{
  "success": false,
  "error": "Invalid Authorization header format. Use: Bearer <token>"
}
```

**Solution:** Ensure header format is exactly `Authorization: Bearer <token>`

#### 3. Invalid API Key (HTTP 403)

```json
{
  "success": false,
  "error": "Invalid API key"
}
```

**Solution:** Verify that your API key matches to `API_KEY` environment variable.

#### 4. Rate Limit Exceeded (HTTP 429)

```json
{
  "error": "Rate limit exceeded: 30 per 1 minute"
}
```

**Solution:** Wait before making more requests. Rate limits reset based on time window.

#### 5. Brute Force Blocked (HTTP 429)

```json
{
  "success": false,
  "error": "Too many failed attempts. Please try again later."
}
```

**Solution:** Wait for the 15-minute block to expire. Do not attempt to bypass the block.

## Usage Examples

### cURL Examples

#### Health Check (Protected)
```bash
curl -X GET \
  http://localhost:42010/ \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Get Emails (Protected)
```bash
curl -X GET \
  "http://localhost:42010/emails?limit=10&skip=0" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Get Specific Email (Protected)
```bash
curl -X GET \
  http://localhost:42010/emails/507f1f77bcf86cd799439011 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Get Attachment (Protected)
```bash
curl -X GET \
  "http://localhost:42010/emails/507f1f77bcf86cd799439011/attachment/document.pdf" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  --output document.pdf
```

#### Webhook (Public - No Authentication)
```bash
curl -X POST \
  http://localhost:42010/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "from": {"email": "sender@example.com"},
    "to": [{"email": "recipient@example.com"}],
    "subject": "Test Email",
    "text": "Email body content"
  }'
```

### Python Examples

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "http://localhost:42010"

# Protected request
headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(f"{BASE_URL}/emails", headers=headers)
print(response.json())
```

### JavaScript/Node.js Examples

```javascript
const axios = require('axios');

const API_KEY = 'your_api_key_here';
const BASE_URL = 'http://localhost:42010';

// Protected request
axios.get(`${BASE_URL}/emails`, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`
  }
})
.then(response => console.log(response.data))
.catch(error => console.error(error));
```

## Security Notes

1. **API Key Storage**: Store your `API_KEY` securely in the `.env` file and never commit it to version control.

2. **HTTPS**: In production, always use HTTPS to transmit your API key securely.

3. **Token Rotation**: Regularly rotate your API keys to maintain security.

4. **Logging**: Failed authentication attempts are logged with partial token information for security monitoring.

5. **Token Strength**: The API key should be a cryptographically secure 256-bit token.

6. **Rate Limit Awareness**: Respect rate limits to avoid being temporarily blocked. Use exponential backoff when handling rate limit errors.

7. **Brute Force Protection**: Multiple failed authentication attempts will temporarily block your IP. Always verify your API key before retrying.

8. **IP-Based Tracking**: Rate limits and brute force protection are IP-based. Multiple users from the same IP share limits.

9. **Storage**: Rate limits and failed attempts are stored in memory and reset on application restart.

## Environment Variables

Required environment variables:

```env
# API Authentication
API_KEY=your_secure_256_bit_token_here

# MongoDB Connection
MONGO_USER=mongo_user
MONGO_PASS=mongo_password
MONGO_HOST=localhost
MONGO_DB=webmail_improvmx
```

## Testing Security Features

### Test Authentication

To test if your API key is working correctly:

```bash
# Test health check
curl -X GET \
  http://localhost:42010/ \
  -H "Authorization: Bearer YOUR_API_KEY"

# Expected response:
# {"status":"healthy","service":"ImprovMX Webhook","timestamp":"2026-10-02T13:25:00.000000"}
```

### Test Rate Limiting

To test rate limiting, make rapid requests to the same endpoint:

```bash
# This should trigger rate limit after 30 requests in 1 minute
for i in {1..40}; do
  curl -X GET http://localhost:42010/ \
    -H "Authorization: Bearer YOUR_API_KEY" &
done
wait
```

### Test Brute Force Protection

To test brute force protection, make multiple failed authentication attempts:

```bash
# 5 invalid attempts should trigger 15-minute block
for i in {1..6}; do
  curl -X GET http://localhost:42010/ \
    -H "Authorization: Bearer INVALID_KEY"
done
```

## Troubleshooting

### "Missing Authorization header"
- Ensure you're sending `Authorization` header
- Check that header name is spelled correctly (case-sensitive)

### "Invalid Authorization header format"
- Verify format is exactly `Authorization: Bearer <token>`
- Ensure there's a space between "Bearer" and the token

### "Invalid API key"
- Double-check that your API key matches `API_KEY` in `.env`
- Ensure `.env` file is being loaded correctly by the application
- Check for trailing spaces or special characters in the token

### "Rate limit exceeded"
- Reduce the frequency of your requests
- Implement caching to avoid redundant requests
- Use exponential backoff when encountering rate limits
- Check if you're sharing an IP with other users (limits are per IP)

### "Too many failed attempts"
- Wait for the 15-minute block to expire
- Verify your API key is correct before retrying
- Check if multiple systems are using the same IP
- Review logs for accidental failed authentication attempts