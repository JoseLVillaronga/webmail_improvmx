from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from pymongo import MongoClient
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}"
client = MongoClient(MONGO_URI)
db = client[os.getenv('MONGO_DB')]
emails_collection = db['emails']

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ImprovMX Webhook',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/webhook', methods=['POST'])
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