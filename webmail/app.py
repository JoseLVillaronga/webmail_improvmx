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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
sent_emails_collection = db['sent_emails']
draft_emails_collection = db['draft_emails']

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


def build_email_query(email_address, aliases=None):
    """Build MongoDB query to filter emails by recipient"""
    if not email_address:
        return {}
    
    # Build list of emails to search (main email + aliases)
    email_list = [email_address]
    if aliases:
        email_list.extend(aliases)
    
    # Create query for each email address
    email_queries = []
    for email in email_list:
        email_queries.append({"to.email": email})
        email_queries.append({"envelope.recipient": email})
    
    # Query for emails where recipient matches any of the emails
    query = {"$or": email_queries}
    return query


@app.route('/')
@login_required
def index():
    """Main page - list of emails filtered by authenticated user email"""
    email_address = get_user_email()
    
    # Pagination parameters
    page = int(request.args.get('page',1))
    per_page = int(request.args.get('per_page', 20))
    
    # Search parameters
    search_query = request.args.get('search', '').strip()
    folder = request.args.get('folder', 'inbox')
    
    # Handle sent and drafts folders
    if folder == 'sent':
        query = {'user_id': current_user.id}
        total_count = sent_emails_collection.count_documents(query)
        emails = list(sent_emails_collection
                      .find(query)
                      .sort('sent_at', -1)
                      .skip((page - 1) * per_page)
                      .limit(per_page))
        
        # Process sent emails for display
        processed_emails = []
        for email in emails:
            processed_email = {
                'id': str(email['_id']),
                'subject': email.get('subject', '(No subject)'),
                'from_name': current_user.email,
                'from_email': current_user.email,
                'to_email': email.get('to', ''),
                'date': email.get('sent_at', datetime.utcnow()),
                'has_attachments': False,
                'unread': False,
                'snippet': email.get('message', '')[:150] + '...' if email.get('message') else ''
            }
            processed_emails.append(processed_email)
        
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
    
    elif folder == 'drafts':
        query = {'user_id': current_user.id}
        total_count = draft_emails_collection.count_documents(query)
        emails = list(draft_emails_collection
                      .find(query)
                      .sort('updated_at', -1)
                      .skip((page - 1) * per_page)
                      .limit(per_page))
        
        # Process draft emails for display
        processed_emails = []
        for email in emails:
            processed_email = {
                'id': str(email['_id']),
                'subject': email.get('subject', '(Borrador sin asunto)'),
                'from_name': current_user.email,
                'from_email': current_user.email,
                'to_email': email.get('to', ''),
                'date': email.get('updated_at', datetime.utcnow()),
                'has_attachments': False,
                'unread': False,
                'snippet': email.get('message', '')[:150] + '...' if email.get('message') else ''
            }
            processed_emails.append(processed_email)
        
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
    
    # Handle inbox/all/unread folders (existing logic)
    # Build base query
    # Admin users see all emails when folder is 'all'
    if is_admin() and folder == 'all':
        query = {}
    else:
        # Get user data including aliases
        user_data = users_collection.find_one({'_id': ObjectId(current_user.id)})
        aliases = user_data.get('aliases', []) if user_data else []
        query = build_email_query(email_address, aliases)
    
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
                    {"text": {"$regex": search_query, "$options": "i"}},
                    {"to.email": {"$regex": search_query, "$options": "i"}},
                    {"envelope.recipient": {"$regex": search_query, "$options": "i"}}
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
        # Get actual recipient from email's 'to' field
        to_list = email.get('to', [])
        if to_list:
            # Use first recipient in 'to' field
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
        # Try to get email from different collections
        email = (emails_collection.find_one({'_id': ObjectId(email_id)}) or
                 sent_emails_collection.find_one({'_id': ObjectId(email_id)}) or
                 draft_emails_collection.find_one({'_id': ObjectId(email_id)}))
        
        if not email:
            return render_template('error.html', 
                                  message='Email not found'), 404
        
        # Verify access: admins can view any email, users can only view their own
        if not is_admin():
            # Check if it's a sent or draft email
            if email in sent_emails_collection.find({'_id': ObjectId(email_id)}) or \
               email in draft_emails_collection.find({'_id': ObjectId(email_id)}):
                # Sent and draft emails must belong to current user
                if email.get('user_id') != current_user.id:
                    return render_template('error.html',
                                          message='Access denied'), 403
            else:
                # Inbox emails: check if recipient matches user or aliases
                user_data = users_collection.find_one({'_id': ObjectId(current_user.id)})
                aliases = user_data.get('aliases', []) if user_data else []
                query = build_email_query(email_address, aliases)
                is_recipient = emails_collection.count_documents({
                    '_id': ObjectId(email_id),
                    "$or": query["$or"]
                }) > 0
                
                if not is_recipient:
                    return render_template('error.html',
                                          message='Access denied'), 403
        
        # Mark as read (only for inbox emails)
        if 'received_at' in email:
            emails_collection.update_one(
                {'_id': ObjectId(email_id)},
                {'$set': {'processed': True}}
            )
        
        # Process email for display
        processed_email = {
            'id': str(email['_id']),
            'subject': email.get('subject', '(No subject)'),
            'from_name': email.get('from', {}).get('name', '') if isinstance(email.get('from'), dict) else email.get('from', ''),
            'from_email': email.get('from', {}).get('email', '') if isinstance(email.get('from'), dict) else email.get('from', ''),
            'to': email.get('to', []),
            'envelope_recipient': email.get('envelope', {}).get('recipient', ''),
            'date': email.get('received_at', email.get('sent_at', email.get('updated_at', datetime.utcnow()))),
            'text': email.get('text', ''),
            'html': email.get('html', email.get('message', '')),
            'headers': email.get('headers', {}),
            'message_id': email.get('message-id', ''),
            'attachments': email.get('attachments', []),
            'inlines': email.get('inlines', []),
            'verdict': email.get('verdict', {}),
            'is_draft': 'created_at' in email,
            'is_sent': 'sent_at' in email
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
            aliases_str = request.form.get('aliases', '').strip()
            smtp_username = request.form.get('smtp_username', '').strip()
            smtp_password = request.form.get('smtp_password', '').strip()
            
            # Parse aliases (comma or newline separated)
            aliases = []
            if aliases_str:
                aliases = [alias.strip() for alias in aliases_str.replace('\n', ',').split(',') if alias.strip()]
            
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
                    'aliases': aliases,
                    'smtp_username': smtp_username,
                    'smtp_password': smtp_password,
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

@app.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit a user"""
    if not is_admin():
        flash('Acceso denegado. Solo administradores.', 'error')
        return redirect(url_for('admin_users'))
    
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('admin_users'))
    
    if str(current_user.id) == user_id:
        flash('No puedes editar tu propio usuario', 'error')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'user')
        password = request.form.get('password', '').strip()
        aliases_str = request.form.get('aliases', '').strip()
        smtp_username = request.form.get('smtp_username', '').strip()
        smtp_password = request.form.get('smtp_password', '').strip()
        
        # Parse aliases (comma or newline separated)
        aliases = []
        if aliases_str:
            aliases = [alias.strip() for alias in aliases_str.replace('\n', ',').split(',') if alias.strip()]
        
        # Build update data
        update_data = {}
        
        if name:
            update_data['name'] = name
        
        if role in ['user', 'admin']:
            update_data['role'] = role
        
        if aliases is not None:  # Always update aliases (can be empty list)
            update_data['aliases'] = aliases
        
        # Update SMTP credentials only if provided (non-empty)
        if smtp_username:
            update_data['smtp_username'] = smtp_username
        
        if smtp_password:
            update_data['smtp_password'] = smtp_password
        
        if password:
            if len(password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres', 'error')
            else:
                update_data['password_hash'] = generate_password_hash(password)
        
        if update_data:
            users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('No se realizaron cambios', 'warning')
    
    return render_template('edit_user.html', user=user_data)


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

@app.route('/compose')
@login_required
def compose():
    """Display compose email form"""
    return render_template('compose.html')


@app.route('/send-email', methods=['POST'])
@login_required
def send_email():
    """Send email via SMTP"""
    logger.info(f"Starting email send process for user {current_user.email}")
    
    # Get form data
    to = request.form.get('to', '').strip()
    cc = request.form.get('cc', '').strip()
    bcc = request.form.get('bcc', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    
    logger.info(f"Email data - To: {to}, Subject: {subject}")
    
    # Validate required fields
    if not to or not subject or not message:
        flash('Por favor completa los campos requeridos', 'error')
        return redirect(url_for('compose'))
    
    # Get user SMTP credentials
    logger.info("Fetching user SMTP credentials...")
    user_data = users_collection.find_one({'_id': ObjectId(current_user.id)})
    smtp_username = user_data.get('smtp_username') if user_data else None
    smtp_password = user_data.get('smtp_password') if user_data else None
    
    logger.info(f"SMTP credentials found: username={smtp_username}, password={'set' if smtp_password else 'not set'}")
    
    if not smtp_username or not smtp_password:
        flash('No tienes configuradas las credenciales SMTP. Contacta al administrador.', 'error')
        return redirect(url_for('compose'))
    
    # Get SMTP configuration from environment
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.improvmx.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_sec_type = os.getenv('SMTP_SEC_TYPE', 'TLS')
    
    logger.info(f"SMTP config: {smtp_server}:{smtp_port}, security={smtp_sec_type}")
    
    try:
        # Create message
        logger.info("Creating email message...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = current_user.email
        msg['To'] = to
        
        if cc:
            msg['Cc'] = cc
        
        # Attach HTML message
        html_part = MIMEText(message, 'html')
        msg.attach(html_part)
        
        logger.info("Connecting to SMTP server...")
        # Connect to SMTP server with timeout
        if smtp_sec_type.upper() == 'TLS':
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            logger.info("Starting TLS...")
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        
        logger.info("Logging in to SMTP server...")
        server.login(smtp_username, smtp_password)
        
        # Prepare recipients list
        recipients = [to]
        if cc:
            recipients.extend([c.strip() for c in cc.split(',') if c.strip()])
        if bcc:
            recipients.extend([b.strip() for b in bcc.split(',') if b.strip()])
        
        logger.info(f"Sending email to {len(recipients)} recipients...")
        # Send email
        server.sendmail(current_user.email, recipients, msg.as_string())
        
        logger.info("Closing SMTP connection...")
        server.quit()
        
        # Save to sent folder
        sent_email = {
            'user_id': current_user.id,
            'from': current_user.email,
            'to': to,
            'cc': cc,
            'bcc': bcc,
            'subject': subject,
            'message': message,
            'sent_at': datetime.utcnow()
        }
        sent_emails_collection.insert_one(sent_email)
        
        flash('Correo enviado exitosamente', 'success')
        return redirect(url_for('index', folder='sent'))
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        flash(f'Error al enviar correo: {str(e)}', 'error')
        return redirect(url_for('compose'))


@app.route('/save-draft', methods=['POST'])
@login_required
def save_draft():
    """Save email as draft"""
    # Get form data
    to = request.form.get('to', '').strip()
    cc = request.form.get('cc', '').strip()
    bcc = request.form.get('bcc', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    
    # Save to drafts folder
    draft_email = {
        'user_id': current_user.id,
        'from': current_user.email,
        'to': to,
        'cc': cc,
        'bcc': bcc,
        'subject': subject,
        'message': message,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    draft_emails_collection.insert_one(draft_email)
    
    flash('Borrador guardado exitosamente', 'success')
    return redirect(url_for('index', folder='drafts'))


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
