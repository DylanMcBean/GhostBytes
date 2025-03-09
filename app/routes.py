from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from datetime import datetime, timezone, timedelta
from .models import User, Message
from . import db, limiter
from .utils import censor_profanity, validate_username, login_required
import re

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return render_template('index.html',messages=Message.query.order_by(Message.timestamp).all())

@main.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm-password', '')

        # List of disallowed usernames
        disallowed_usernames = ['admin', 'administrator', 'root', 'system', 'moderator', 
                                'support', 'staff', 'official', 'sysadmin', 'superuser']
        
        # Validation checks
        if username.lower() in disallowed_usernames:
            flash('This username is not allowed.')
            return redirect(url_for('main.register'))

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('main.register'))

        if not validate_username(username):
            flash('Invalid username, must be 3-20 characters long and contain only letters, numbers, and . or -')
            return redirect(url_for('main.register'))
            
        # Validate email format
        if not re.match(r'^[\w.-]+@[a-zA-Z\d.-]+\.[a-zA-Z]{2,}$', email):
            flash('Please enter a valid email address.')
            return redirect(url_for('main.register'))

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username is taken.')
            return redirect(url_for('main.register'))
            
        if User.query.filter_by(email_address=email).first():
            flash('Email address is already registered.')
            return redirect(url_for('main.register'))

        # Create new user with updated model structure
        user = User(
            username=username,
            email_address=email,
            status='offline',
            two_factor_state=0,  # Unset
            must_change_password=False,
            failed_login_attempts=0,
            active=True,
            last_password_change=datetime.now(timezone.utc)
        )
        
        # Set password and generate session secret
        user.set_password(password)
        user.generate_session_secret()
        
        # Add user to database
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful.')
        return redirect(url_for('main.login'))

    return render_template('auth.html', mode='register')

@main.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute, 15 per hour")
def login():
    if request.method == 'POST':
        login_identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.username == login_identifier) | 
            (User.email_address == login_identifier)
        ).first()

        if not user or not user.check_password(password):
            if user:
                user.failed_login_attempts += 1
                db.session.commit()
            flash('Invalid credentials.')
            return redirect(url_for('main.login'))

        if not user.active:
            flash('Account disabled.')
            return redirect(url_for('main.login'))
        
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            flash('Account locked. Please try again later.')
            return redirect(url_for('main.login'))
        
        # TODO Implement account lockout with catchpa
        if user.failed_login_attempts >= 5:
            flash('Too many failed login attempts. Account locked.')
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            db.session.commit()
            return redirect(url_for('main.login'))
        
        user_secret = user.generate_session_secret()
        user.last_login = datetime.now(timezone.utc)
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()

        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_secret'] = user_secret

        return redirect(url_for('main.index'))

    return render_template('auth.html', mode='login')

@main.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@main.route('/messages', methods=['POST'])
@limiter.limit("1 per second")
@login_required
def create_message():
    data = request.get_json()
    content = data.get('content', '').strip()
    parent_message_id = data.get('parent_message_id', None)
    channel_id = 1  # data.get('channel_id')

    if not content:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if not channel_id:
        return jsonify({'error': 'Channel ID is required'}), 400

    content = censor_profanity(content)
    message = Message(
        user_id=session['user_id'],
        channel_id=channel_id,
        content=content,
        parent_message_id=parent_message_id
    )
    db.session.add(message)

    # Delete messages older than 12 hours
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
    Message.query.filter(Message.timestamp < two_hours_ago).delete()

    db.session.commit()

    parent_message = None
    if parent_message_id:
        parent_message = Message.query.get(parent_message_id)

    return jsonify({
        'id': message.id,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'username': session['username'],
        'channel_id': message.channel_id,
        'parent_message_id': message.parent_message_id,
        'parent': {
            'username': parent_message.author.username if parent_message else None,
            'content': parent_message.content if parent_message else None
        }
    }), 201

@main.route('/messages/recent')
@login_required
def get_recent_messages():
    after_id = request.args.get('after', type=int)
    channel_id = 1 # request.args.get('channel_id', type=int)

    if not channel_id:
        return jsonify({'error': 'Channel ID is required'}), 400

    query = Message.query.filter_by(channel_id=channel_id).order_by(Message.timestamp.asc())

    if after_id:
        last_message = Message.query.get(after_id)
        if last_message:
            query = query.filter(Message.timestamp > last_message.timestamp)

    messages = query.limit(50).all()

    return jsonify([{
        'id': m.id,
        'content': m.content,
        'timestamp': m.timestamp.isoformat(),
        'username': m.author.username,
        'channel_id': m.channel_id
    } for m in messages])