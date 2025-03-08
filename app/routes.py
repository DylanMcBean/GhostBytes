from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from datetime import datetime, timezone, timedelta
from .models import User, Message
from . import db, limiter
from .utils import censor_profanity, validate_username, login_required

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    raw_messages = Message.query.order_by(Message.timestamp).all()
    grouped_messages = []
    last_message_id = None

    # Group messages from the same user if sent within 60 seconds
    for message in raw_messages:
        message.content = censor_profanity(message.content)
        if (not grouped_messages or 
            message.user_id != grouped_messages[-1].user_id or
            (message.timestamp - grouped_messages[-1].timestamp).total_seconds() > 60):
            grouped_messages.append(message)
        else:
            grouped_messages[-1].content += f"\n{message.content}"
        last_message_id = message.id

    return render_template('index.html',
                           username=session.get('username'),
                           messages=grouped_messages,
                           last_message_id=last_message_id)

@main.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm-password', '')

        disallowed_usernames = ['admin', 'administrator', 'root', 'system', 'moderator', 
                                'support', 'staff', 'official', 'sysadmin', 'superuser']
        
        if username.lower() in disallowed_usernames:
            flash('This username is not allowed.')
            return redirect(url_for('main.register'))

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('main.register'))

        if not validate_username(username):
            flash('Invalid username, must be 3-20 characters long and contain only letters, numbers, and . or -')
            return redirect(url_for('main.register'))

        if User.query.filter_by(username=username).first():
            flash('Username is taken.')
            return redirect(url_for('main.register'))

        user = User(username=username)
        user.set_password(password)
        user.generate_session_secret()
        db.session.add(user)
        db.session.commit()
        flash('Registration successful.')
        return redirect(url_for('main.login'))

    return render_template('auth.html', mode='register')

@main.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Invalid credentials.')
            return redirect(url_for('main.login'))

        if not user.active:
            flash('Account disabled.')
            return redirect(url_for('main.login'))
        
        user_secret = user.generate_session_secret()
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_secret'] = user_secret
        print(session)

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

    if not content:
        return jsonify({'error': 'Message cannot be empty'}), 400

    content = censor_profanity(content)
    message = Message(user_id=session['user_id'], content=content)
    db.session.add(message)


    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    Message.query.filter(Message.timestamp < two_hours_ago).delete()

    db.session.commit()

    return jsonify({
        'id': message.id,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'username': session['username'],
        'isUser': True
    }), 201

@main.route('/messages/recent')
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
