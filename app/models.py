from datetime import datetime, timezone
from . import db
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True, nullable=False)
    user_secret = db.Column(db.String(64), nullable=True)
    messages = relationship('Message', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_session_secret(self):
        self.user_secret = generate_password_hash(str(datetime.now(timezone.utc)) + uuid.uuid4().hex)
        return self.user_secret

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
