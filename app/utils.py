import re
from functools import wraps
from datetime import datetime, timezone
from flask import session, redirect, url_for, request, flash
from .models import User

def censor_profanity(text):
    profanity_list = {
        "gay": "coconut milk",
        "fgt": "lieutenant",
        "nigger": "fine sir",
        "loli": "fine lady",
        "fuck": "duck",
        "fucking": "fun time",
        "dildo": "poporing",
        "faggot": "lamborghini",
        "cunt": "ant hill",
        "fag": "cigarette"
    }
    censored_text = text
    for word, replacement in profanity_list.items():
        pattern = r'\b' + re.escape(word) + r'\b'
        censored_text = re.sub(pattern, replacement, censored_text, flags=re.IGNORECASE)
    return censored_text

def validate_username(username):
    return re.match(r'^[\w.-]{3,20}$', username)

def validate_session():
    if 'user_id' not in session or 'user_secret' not in session:
        return False
    
    user = User.query.get(session['user_id'])
    if not user:
        return False
    
    return user.user_secret == session.get('user_secret')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_session():
            session.clear()
            flash('Your session has expired or is invalid. Please login again.')
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
