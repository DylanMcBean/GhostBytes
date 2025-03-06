from flask import Flask
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
    
    # Import models to register them with SQLAlchemy and create tables
    with app.app_context():
        from . import models
        db.create_all()
    
    # Register blueprint(s)
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app