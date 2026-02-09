"""
Webmail Application - ImprovMX
A webmail interface to view emails stored in MongoDB
"""

from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
import logging
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

# MongoDB connection
MONGO_USER = os.getenv('MONGO_USER', 'Admin')
MONGO_PASS = os.getenv('MONGO_PASS', '')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_DB = os.getenv('MONGO_DB', 'webmail_improvmx')

MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}"
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
emails_collection = db['emails']
users_collection = db['users']

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_dict):
        self.id = str(user_dict['_id'])
        self.email = user_dict['email']
        self.name = user_dict.get('name', '')
        self.role = user_dict.get('role', 'user')
        self.password_hash = user_dict['password_hash']

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

def initialize_default_admin():
    """Create default webmaster user if no users exist"""
    if users_collection.count_documents({}) == 0:
        default_admin = {
            'email': 'webmaster',
            'password_hash': generate_password_hash('admin123'),
            'name': 'Webmaster',
            'role': 'admin',
            'created_at': datetime.utcnow()
        }
        users_collection.insert_one(default_admin)
        logging.info("Default admin user created: webmaster / admin123")


def get_user_email():
    """Get email from authenticated user"""
    return current_user.email

def is_admin():
    """Check if current user is admin"""
    return current_user.is_authenticated and current_user.role == 'admin'


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
@login_required
def index():
    """Main page - list of emails filtered by authenticated user email"""
    email_address = get_user_email()
    
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
@login_required
def view_email(email_id):
    """View a specific email"""
    email_address = get_user_email()
    
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Por favor ingresa email y contraseña', 'error')
            return render_template('login.html')
        
        user_data = users_collection.find_one({'email': email})
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user's own password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son requeridos', 'error')
        elif len(new_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'error')
        elif new_password != confirm_password:
            flash('La nueva contraseña y la confirmación no coinciden', 'error')
        else:
            # Verify current password
            user_data = users_collection.find_one({'_id': ObjectId(current_user.id)})
            
            if not check_password_hash(user_data['password_hash'], current_password):
                flash('La contraseña actual es incorrecta', 'error')
            else:
                # Update password
                new_password_hash = generate_password_hash(new_password)
                users_collection.update_one(
                    {'_id': ObjectId(current_user.id)},
                    {'$set': {'password_hash': new_password_hash}}
                )
                flash('Contraseña cambiada exitosamente', 'success')
                return redirect(url_for('index'))
    
    return render_template('change_password.html')

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    """Admin page to manage users"""
    if not is_admin():
        flash('Acceso denegado. Solo administradores.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            name = request.form.get('name', '').strip()
            role = request.form.get('role', 'user')
            
            if not email or not password:
                flash('Email y contraseña son requeridos', 'error')
            elif users_collection.find_one({'email': email}):
                flash('El email ya existe', 'error')
            else:
                new_user = {
                    'email': email,
                    'password_hash': generate_password_hash(password),
                    'name': name,
                    'role': role,
                    'created_at': datetime.utcnow()
                }
                users_collection.insert_one(new_user)
                flash(f'Usuario {email} creado exitosamente', 'success')
        
        elif action == 'delete':
            user_id = request.form.get('user_id')
            if user_id:
                if str(current_user.id) == user_id:
                    flash('No puedes eliminar tu propio usuario', 'error')
                else:
                    users_collection.delete_one({'_id': ObjectId(user_id)})
                    flash('Usuario eliminado exitosamente', 'success')
    
    users = list(users_collection.find())
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<user_id>/toggle-role', methods=['POST'])
@login_required
def toggle_user_role(user_id):
    """Toggle user role between admin and user"""
    if not is_admin():
        return jsonify({'error': 'Acceso denegado'}), 403
    
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    if str(current_user.id) == user_id:
        return jsonify({'error': 'No puedes cambiar tu propio rol'}), 400
    
    new_role = 'user' if user_data.get('role') == 'admin' else 'admin'
    users_collection.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'role': new_role}}
    )
    
    return jsonify({'success': True, 'new_role': new_role})

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
    # Initialize default admin if no users exist
    initialize_default_admin()
    
    # For development only
    app.run(host='0.0.0.0', port=26000, debug=True)
