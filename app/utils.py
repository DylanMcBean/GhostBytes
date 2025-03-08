import re
from functools import wraps
from datetime import datetime, timezone
from flask import session, redirect, url_for, request, flash

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
