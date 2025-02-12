from .extensions import db
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask import current_app
import uuid

class Feed(db.Model):
    __tablename__ = 'feeds'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String, unique=True)
    name = db.Column(db.String)
    category = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)
    articles = db.relationship('Article', backref='feed', lazy=True)

class Article(db.Model):
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feeds.id'))
    title = db.Column(db.String)
    url = db.Column(db.String, unique=True)
    published = db.Column(db.DateTime)
    summary = db.Column(db.Text)
    content = db.Column(db.Text)
    author = db.Column(db.String)
    
class DailySummary(db.Model):
    __tablename__ = 'daily_summaries'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.String, nullable=False)
    summary = db.Column(db.JSON, nullable=False)
    generated_at = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    commentary = db.Column(db.Text)
    summary_type = db.Column(db.String, nullable=False, default='daily')

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100), unique=True)
    password_reset_expires = db.Column(db.DateTime)
    
    sessions = db.relationship('UserSession', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_auth_token(self, expires_in=86400):
        return jwt.encode(
            {
                'user_id': self.id,
                'username': self.username,
                'role': self.role,
                'exp': datetime.utcnow() + timedelta(seconds=expires_in)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    def generate_password_reset_token(self):
        self.password_reset_token = str(uuid.uuid4())
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        return self.password_reset_token
    
    def clear_password_reset_token(self):
        self.password_reset_token = None
        self.password_reset_expires = None
        db.session.commit()
    
    def increment_failed_attempts(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= current_app.config.get('MAX_FAILED_ATTEMPTS', 5):
            self.locked_until = datetime.utcnow() + timedelta(
                minutes=current_app.config.get('ACCOUNT_LOCKOUT_MINUTES', 30)
            )
        db.session.commit()
    
    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        if self.locked_until:  # Lock period has expired
            self.reset_failed_attempts()
        return False

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    
    @staticmethod
    def create_session(user, token, ip_address=None, user_agent=None):
        session = UserSession(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=1),
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(session)
        db.session.commit()
        return session
    
    def deactivate(self):
        self.is_active = False
        db.session.commit()

    @staticmethod
    def cleanup_expired():
        UserSession.query.filter(
            (UserSession.expires_at < datetime.utcnow()) |
            (UserSession.is_active == False)
        ).delete()
        db.session.commit()