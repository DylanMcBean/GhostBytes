from datetime import datetime, timezone
from . import db
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    email_address = db.Column(db.String(254), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    two_factor_state = db.Column(db.SmallInteger, default=0, nullable=False)  # Unset, Set, Pending
    two_factor_secret = db.Column(db.String(128))  # only set when two_factor_state is not "Unset"
    status = db.Column(db.String(10), default='offline', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_attempts = db.Column(db.SmallInteger, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime)
    last_password_change = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Keep the user_secret for session handling (from the original code)
    user_secret = db.Column(db.String(64), nullable=True)
    
    # Relationships
    messages = relationship('Message', backref='author', lazy=True, foreign_keys='Message.user_id')
    owned_channels = relationship('Channel', backref='creator', lazy=True)
    encryption_keys = relationship('EncryptionKey', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        self.last_password_change = datetime.now(timezone.utc)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_session_secret(self):
        self.user_secret = secrets.token_hex(32)
        return self.user_secret
    
    def __repr__(self):
        return f'<User {self.username}>'


class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    is_private = db.Column(db.Boolean, default=False, nullable=False)
    encryption_key_id = db.Column(db.Integer, db.ForeignKey('encryption_keys.id', ondelete='SET NULL'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    members = relationship('ChannelMember', backref='channel', lazy=True, cascade='all, delete-orphan')
    messages = relationship('Message', backref='channel', lazy=True, cascade='all, delete-orphan')
    encryption_key = relationship('EncryptionKey')
    
    def __repr__(self):
        return f'<Channel {self.name}>'


class ChannelMember(db.Model):
    __tablename__ = 'channel_members'
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role = db.Column(db.String(10), default='member', nullable=False)  # owner, admin, moderator, member
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship('User')
    
    def __repr__(self):
        return f'<ChannelMember {self.user_id} in {self.channel_id}>'


class EncryptionKey(db.Model):
    __tablename__ = 'encryption_keys'
    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    key_material = db.Column(db.String(512), nullable=False)
    key_type = db.Column(db.String(10), default='personal', nullable=False)  # personal, shared, channel
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    access_users = relationship('EncryptionKeyAccess', backref='key', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EncryptionKey {self.id}>'


class EncryptionKeyAccess(db.Model):
    __tablename__ = 'encryption_key_access'
    encryption_key_id = db.Column(db.Integer, db.ForeignKey('encryption_keys.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    granted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship('User')
    
    def __repr__(self):
        return f'<EncryptionKeyAccess {self.encryption_key_id}-{self.user_id}>'


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='SET NULL'))
    content = db.Column(db.String(2000), nullable=False)
    encryption_key_id = db.Column(db.Integer, db.ForeignKey('encryption_keys.id', ondelete='SET NULL'))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    edited_at = db.Column(db.DateTime)
    has_mention = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    replies = relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy=True)
    encryption_key = relationship('EncryptionKey')
    mentions = relationship('MessageMention', backref='message', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Message {self.id}>'


class MessageMention(db.Model):
    __tablename__ = 'message_mentions'
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    
    # Relationships
    user = relationship('User')
    
    def __repr__(self):
        return f'<MessageMention {self.message_id}-{self.user_id}>'