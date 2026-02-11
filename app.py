from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
import base64
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# API Key for authentication
API_KEY = os.getenv('API_KEY')

# Brute force protection: Track failed auth attempts
failed_attempts = {}  # {ip: {'count': int, 'blocked_until': datetime or None}}
BLOCK_DURATION = timedelta(minutes=15)  # Block for 15 minutes
MAX_ATTEMPTS = 5  # Maximum failed attempts
ATTEMPT_WINDOW = timedelta(minutes=5)  # Count attempts in this window

def check_brute_force_protection(ip):
    """Check if IP is blocked due to brute force"""
    if ip not in failed_attempts:
        return False
    
    # Clean up old attempts
    now = datetime.utcnow()
    failed_attempts[ip]['attempts'] = [
        attempt for attempt in failed_attempts[ip]['attempts']
        if now - attempt < ATTEMPT_WINDOW
    ]
    
    # Check if blocked
    if failed_attempts[ip].get('blocked_until') and now < failed_attempts[ip]['blocked_until']:
        remaining_time = (failed_attempts[ip]['blocked_until'] - now).total_seconds()
        return remaining_time
    
    # Remove block if expired
    if failed_attempts[ip].get('blocked_until') and now >= failed_attempts[ip]['blocked_until']:
        failed_attempts[ip]['blocked_until'] = None
        failed_attempts[ip]['count'] = 0
    
    return False

def record_failed_attempt(ip):
    """Record a failed authentication attempt"""
    now = datetime.utcnow()
    if ip not in failed_attempts:
        failed_attempts[ip] = {
            'count': 0,
            'attempts': [],
            'blocked_until': None
        }
    
    failed_attempts[ip]['count'] += 1
    failed_attempts[ip]['attempts'].append(now)
    
    # Clean old attempts
    failed_attempts[ip]['attempts'] = [
        attempt for attempt in failed_attempts[ip]['attempts']
        if now - attempt < ATTEMPT_WINDOW
    ]
    
    # Check if should block
    if failed_attempts[ip]['count'] >= MAX_ATTEMPTS:
        failed_attempts[ip]['blocked_until'] = now + BLOCK_DURATION
        logger.warning(f"IP {ip} blocked for {BLOCK_DURATION.total_seconds()}s due to {MAX_ATTEMPTS} failed attempts")

def clear_failed_attempts(ip):
    """Clear failed attempts on successful auth"""
    if ip in failed_attempts:
        del failed_attempts[ip]

def require_api_key(f):
    """Decorator to require API key authentication with brute force protection"""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        
        # Check brute force protection
        block_remaining = check_brute_force_protection(ip)
        if block_remaining:
            logger.warning(f"Blocked IP {ip} attempting access: {block_remaining:.0f}s remaining")
            return jsonify({
                'success': False,
                'error': 'Too many failed attempts. Please try again later.'
            }), 429
        
        # Get API key from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("Missing Authorization header")
            record_failed_attempt(ip)
            return jsonify({
                'success': False,
                'error': 'Missing Authorization header'
            }), 401
        
        # Check if it's a Bearer token
        if not auth_header.startswith('Bearer '):
            logger.warning("Invalid Authorization header format")
            record_failed_attempt(ip)
            return jsonify({
                'success': False,
                'error': 'Invalid Authorization header format. Use: Bearer <token>'
            }), 401
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        # Verify token
        if token != API_KEY:
            logger.warning(f"Invalid API key attempt: {token[:8]}...")
            record_failed_attempt(ip)
            return jsonify({
                'success': False,
                'error': 'Invalid API key'
            }), 403
        
        # Valid authentication - clear failed attempts
        clear_failed_attempts(ip)
        
        # Token is valid, proceed with function
        return f(*args, **kwargs)
    
    return decorated

# MongoDB connection
MONGO_URI = f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}"
client = MongoClient(MONGO_URI)
db = client[os.getenv('MONGO_DB')]
emails_collection = db['emails']

@app.route('/', methods=['GET'])
@require_api_key
@limiter.limit("30 per minute")  # Health check can be called frequently
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ImprovMX Webhook',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/docs', methods=['GET'])
@limiter.limit("60 per minute")  # Docs can be accessed frequently
def api_docs():
    """API Documentation endpoint - returns the API_AUTHENTICATION.md file"""
    try:
        # Read the documentation file
        docs_path = os.path.join(os.path.dirname(__file__), 'API_AUTHENTICATION.md')
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_content = f.read()
        
        # Return as markdown content with proper content type
        return make_response(docs_content, 200)
    except FileNotFoundError:
        return jsonify({
            'error': 'Documentation file not found'
        }), 404
    except Exception as e:
        logger.error(f"Error reading documentation: {str(e)}")
        return jsonify({
            'error': 'Error reading documentation'
        }), 500

@app.route('/webhook', methods=['POST'])
@limiter.limit("200 per minute")  # High limit for ImprovMX webhook
def receive_email():
    """
    Webhook endpoint to receive emails from ImprovMX
    """
    try:
        # Parse the incoming JSON data
        email_data = request.get_json()
        
        if not email_data:
            logger.warning("Received empty request")
            return jsonify({'error': 'No data received'}), 400
        
        logger.info(f"Received email from {email_data.get('from', {}).get('email', 'unknown')}")
        logger.info(f"Subject: {email_data.get('subject', 'No subject')}")
        
        # Add metadata
        email_data['received_at'] = datetime.utcnow()
        email_data['processed'] = False
        
        # Insert into MongoDB
        result = emails_collection.insert_one(email_data)
        
        logger.info(f"Email saved to MongoDB with ID: {result.inserted_id}")
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Email received and stored',
            'email_id': str(result.inserted_id)
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/emails', methods=['GET'])
@require_api_key
@limiter.limit("20 per minute")  # Standard rate for email retrieval
def get_emails():
    """
    Retrieve stored emails from MongoDB
    Query parameters:
    - limit: number of emails to return (default: 10)
    - skip: number of emails to skip (default: 0)
    - from_email: filter by sender email
    - subject: filter by subject (partial match)
    """
    try:
        limit = int(request.args.get('limit', 10))
        skip = int(request.args.get('skip', 0))
        from_email = request.args.get('from_email')
        subject = request.args.get('subject')
        
        # Build query
        query = {}
        if from_email:
            query['from.email'] = from_email
        if subject:
            query['subject'] = {'$regex': subject, '$options': 'i'}
        
        # Fetch emails
        emails = list(emails_collection.find(query).sort('received_at', -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string and format datetime
        for email in emails:
            email['_id'] = str(email['_id'])
            if 'received_at' in email:
                email['received_at'] = email['received_at'].isoformat()
        
        return jsonify({
            'success': True,
            'count': len(emails),
            'emails': emails
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving emails: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/emails/<email_id>', methods=['GET'])
@require_api_key
@limiter.limit("30 per minute")  # Slightly higher for viewing individual emails
def get_email(email_id):
    """
    Retrieve a specific email by ID
    """
    try:
        from bson.objectid import ObjectId
        email = emails_collection.find_one({'_id': ObjectId(email_id)})
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'Email not found'
            }), 404
        
        email['_id'] = str(email['_id'])
        if 'received_at' in email:
            email['received_at'] = email['received_at'].isoformat()
        
        return jsonify({
            'success': True,
            'email': email
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving email: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/emails/<email_id>/attachment/<attachment_name>', methods=['GET'])
@require_api_key
@limiter.limit("10 per minute")  # Lower limit for downloads (resource intensive)
def get_attachment(email_id, attachment_name):
    """
    Retrieve a specific attachment from an email
    """
    try:
        from bson.objectid import ObjectId
        email = emails_collection.find_one({'_id': ObjectId(email_id)})
        
        if not email:
            return jsonify({'error': 'Email not found'}), 404
        
        # Search in attachments
        for attachment in email.get('attachments', []):
            if attachment['name'] == attachment_name:
                content = base64.b64decode(attachment['content'])
                from flask import Response
                return Response(
                    content,
                    mimetype=attachment['type'],
                    headers={'Content-Disposition': f'attachment; filename="{attachment_name}"'}
                )
        
        # Search in inlines
        for inline in email.get('inlines', []):
            if inline['name'] == attachment_name:
                content = base64.b64decode(inline['content'])
                from flask import Response
                return Response(
                    content,
                    mimetype=inline['type'],
                    headers={'Content-Disposition': f'inline; filename="{attachment_name}"'}
                )
        
        return jsonify({'error': 'Attachment not found'}), 404
        
    except Exception as e:
        logger.error(f"Error retrieving attachment: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # For development only
    app.run(host='0.0.0.0', port=42010, debug=True)