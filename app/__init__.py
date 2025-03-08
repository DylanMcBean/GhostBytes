from flask import Flask, flash, redirect, request, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config import Config

db = SQLAlchemy()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        flash('Too many requests. Please slow down.', 'error')
        # Render the current template instead of redirecting
        if request.endpoint == 'main.login':
            return render_template('auth.html', mode='login')
        elif request.endpoint == 'main.register':
            return render_template('auth.html', mode='register')
        else:
            return redirect(url_for('main.index'))
    
    # Import models to register them with SQLAlchemy and create tables
    with app.app_context():
        from . import models
        db.create_all()
    
    # Register blueprint(s)
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app