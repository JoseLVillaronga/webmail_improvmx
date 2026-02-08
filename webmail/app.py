"""
Webmail Application - ImprovMX
A webmail interface to view emails stored in MongoDB
"""

from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# MongoDB connection
MONGO_USER = os.getenv('MONGO_USER', 'Admin')
MONGO_PASS = os.getenv('MONGO_PASS', '')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_DB = os.getenv('MONGO_DB', 'webmail_improvmx')

MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}"
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
emails_collection = db['emails']


def get_email_from_request():
    """Get email from query parameter or return None"""
    return request.args.get('email')


def build_email_query(email_address):
    """Build MongoDB query to filter emails by recipient"""
    if not email_address:
        return {}
    
    # Query for emails where recipient matches either to[].email or envelope.recipient
    query = {
        "$or": [
            {"to.email": email_address},
            {"envelope.recipient": email_address}
        ]
    }
    return query


@app.route('/')
def index():
    """Main page - list of emails filtered by email parameter"""
    email_address = get_email_from_request()
    
    if not email_address:
        return render_template('no_email.html'), 400
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # Search parameters
    search_query = request.args.get('search', '').strip()
    folder = request.args.get('folder', 'inbox')
    
    # Build base query
    query = build_email_query(email_address)
    
    # Add folder filter (all/inbox/unread)
    if folder == 'unread':
        query['processed'] = False
    # 'inbox' and 'all' show all emails
    
    # Add search filter if provided
    if search_query:
        query['$and'] = [
            {
                "$or": [
                    {"subject": {"$regex": search_query, "$options": "i"}},
                    {"from.email": {"$regex": search_query, "$options": "i"}},
                    {"text": {"$regex": search_query, "$options": "i"}}
                ]
            }
        ]
    
    # Calculate skip value for pagination
    skip = (page - 1) * per_page
    
    # Fetch emails
    total_count = emails_collection.count_documents(query)
    emails = list(emails_collection
                  .find(query)
                  .sort('received_at', -1)
                  .skip(skip)
                  .limit(per_page))
    
    # Process emails for display
    processed_emails = []
    for email in emails:
        # Get actual recipient from the email's 'to' field
        to_list = email.get('to', [])
        if to_list:
            # Use first recipient in the 'to' field
            to_email = to_list[0].get('email', '') if isinstance(to_list[0], dict) else str(to_list[0])
        else:
            # Fallback to envelope recipient if no 'to' field
            to_email = email.get('envelope', {}).get('recipient', '')
        
        processed_email = {
            'id': str(email['_id']),
            'subject': email.get('subject', '(No subject)'),
            'from_name': email.get('from', {}).get('name', ''),
            'from_email': email.get('from', {}).get('email', ''),
            'to_email': to_email,
            'date': email.get('received_at', datetime.utcnow()),
            'has_attachments': len(email.get('attachments', [])) > 0,
            'unread': not email.get('processed', True),
            'snippet': email.get('text', '')[:150] + '...' if email.get('text') else ''
        }
        processed_emails.append(processed_email)
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('index.html',
                          email_address=email_address,
                          emails=processed_emails,
                          page=page,
                          per_page=per_page,
                          total_pages=total_pages,
                          total_count=total_count,
                          search_query=search_query,
                          folder=folder)


@app.route('/view/<email_id>')
def view_email(email_id):
    """View a specific email"""
    email_address = get_email_from_request()
    
    if not email_address:
        return render_template('no_email.html'), 400
    
    try:
        # Get email from MongoDB
        email = emails_collection.find_one({'_id': ObjectId(email_id)})
        
        if not email:
            return render_template('error.html', 
                                  message='Email not found'), 404
        
        # Verify email belongs to the requested recipient
        query = build_email_query(email_address)
        is_recipient = emails_collection.count_documents({
            '_id': ObjectId(email_id),
            "$or": query["$or"]
        }) > 0
        
        if not is_recipient:
            return render_template('error.html',
                                  message='Access denied'), 403
        
        # Mark as read
        emails_collection.update_one(
            {'_id': ObjectId(email_id)},
            {'$set': {'processed': True}}
        )
        
        # Process email for display
        processed_email = {
            'id': str(email['_id']),
            'subject': email.get('subject', '(No subject)'),
            'from_name': email.get('from', {}).get('name', ''),
            'from_email': email.get('from', {}).get('email', ''),
            'to': email.get('to', []),
            'envelope_recipient': email.get('envelope', {}).get('recipient', ''),
            'date': email.get('received_at', datetime.utcnow()),
            'text': email.get('text', ''),
            'html': email.get('html', ''),
            'headers': email.get('headers', {}),
            'message_id': email.get('message-id', ''),
            'attachments': email.get('attachments', []),
            'inlines': email.get('inlines', []),
            'verdict': email.get('verdict', {})
        }
        
        # Format inline images for HTML display
        inline_map = {inline.get('cid'): inline for inline in processed_email['inlines']}
        
        return render_template('view_email.html',
                              email_address=email_address,
                              email=processed_email,
                              inline_map=inline_map)
        
    except Exception as e:
        logger.error(f"Error viewing email: {str(e)}")
        return render_template('error.html',
                              message=f'Error loading email: {str(e)}'), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        client.server_info()
        return jsonify({
            'status': 'healthy',
            'service': 'Webmail Application',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message='Internal server error'), 500


if __name__ == '__main__':
    # For development only
    app.run(host='0.0.0.0', port=26000, debug=True)