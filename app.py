from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy.orm import relationship
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import re
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-insecure')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

csrf = CSRFProtect(app)
db = SQLAlchemy(app)
# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
)

# Profanity censoring helper
def censor_profanity(text):
    profanity_list = {
        "gay": "coconut milk",
        "fgt": "lieutenant",
        "nigger": "fine sir",
        "loli": "fine lady",
        "fuck": "duck",
        "dildo": "poporing",
        "faggot": "lamborghini",
        "cunt": "ant hill",
        "fag": "cigarette"
    }
    censored_text = text
    for word in profanity_list.keys():
        pattern = r'\b' + re.escape(word) + r'\b'
        replacement = profanity_list[word]
        censored_text = re.sub(pattern, replacement, censored_text, flags=re.IGNORECASE)
    return censored_text

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True, nullable=False)
    messages = relationship('Message', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

with app.app_context():
    db.create_all()

# Security Helpers
def validate_username(username):
    return re.match(r'^[\w.-]{3,20}$', username)

def validate_password(password):
    return len(password) >= 8 and any(c.isupper() for c in password)

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    raw_messages = Message.query.order_by(Message.timestamp).all()
    grouped_messages = []
    
    # Group messages from the same user if sent within 60 seconds
    last_message_id = None
    for message in raw_messages:
        if (not grouped_messages or 
            message.user_id != grouped_messages[-1].user_id or
            (message.timestamp - grouped_messages[-1].timestamp).total_seconds() > 60):
            # Start a new group with this message
            grouped_messages.append(message)
        else:
            # Append content to the last message in the group
            grouped_messages[-1].content += f"\n{message.content}"
        last_message_id = message.id
    print(last_message_id)
    
    return render_template('index.html',
                         username=session.get('username'),
                         messages=grouped_messages,
                         last_message_id=last_message_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm-password', '')

        # List of disallowed usernames
        disallowed_usernames = ['admin', 'administrator', 'root', 'system', 'moderator', 
                               'support', 'staff', 'official', 'sysadmin', 'superuser']
        
        if username.lower() in disallowed_usernames:
            flash('This username is not allowed.')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('register'))

        if not validate_username(username):
            flash('Invalid username.')
            return redirect(url_for('register'))

        if not validate_password(password):
            flash('Invalid password, must be at least 8 characters long and contain an uppercase letter.')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username is taken.')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful.')
        return redirect(url_for('login'))

    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Invalid credentials.')
            return redirect(url_for('login'))

        if not user.active:
            flash('Account disabled.')
            return redirect(url_for('login'))

        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('auth.html', mode='login')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

# Modify the create_message route
@app.route('/messages', methods=['POST'])
@limiter.limit("1 per second")
@login_required
def create_message():
    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Message cannot be empty'}), 400

    content = censor_profanity(content)

    # Create new message
    message = Message(user_id=session['user_id'], content=content)
    db.session.add(message)

    # Delete messages older than 2 hours (UTC)
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    Message.query.filter(Message.timestamp < two_hours_ago).delete()

    # Commit both operations at once
    db.session.commit()

    return jsonify({
        'id': message.id,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'username': session['username'],
        'isUser': True
    }), 201


@app.route('/messages/recent')
@login_required
def get_recent_messages():
    after_id = request.args.get('after', type=int)
    query = Message.query.order_by(Message.timestamp.asc())

    if after_id:
        last_message = Message.query.get(after_id)
        if last_message:
            query = query.filter(Message.timestamp > last_message.timestamp)

    messages = query.limit(50).all()

    return jsonify([{
        'id': m.id,
        'content': m.content,
        'timestamp': m.timestamp.isoformat(),
        'username': m.user.username,
        'isUser': m.user.username == session['username']
    } for m in messages])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
