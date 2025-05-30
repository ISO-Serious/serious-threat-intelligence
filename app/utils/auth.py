from functools import wraps
from flask import session, redirect, url_for, request, jsonify, current_app, g
from app.models import User, UserSession, APIToken
import jwt
from datetime import datetime
from app.models import APIToken


def requires_auth_or_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # First check for API token
        api_token = request.headers.get('X-API-Token')
        if api_token:
            token = APIToken.query.filter_by(token=api_token, is_active=True).first()
            if token:
                token.update_last_used()
                return f(*args, **kwargs)
        
        # If no valid API token, check for session auth
        auth_token = session.get('auth_token')
        if not auth_token:
            return jsonify({'error': 'Authentication required'}), 401
            
        try:
            # Your existing session token validation logic
            payload = jwt.decode(
                auth_token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
                
            return f(*args, **kwargs)
            
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid session'}), 401
            
    return decorated

def get_current_user_from_token(auth_token):
    """Helper function to get user from token"""
    try:
        payload = jwt.decode(
            auth_token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return User.query.get(payload['user_id'])
    except jwt.InvalidTokenError:
        return None

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Keep the email2 endpoint public
        if request.endpoint == 'web.email2':
            return f(*args, **kwargs)
        
        auth_token = session.get('auth_token')
        if not auth_token:
            # For API requests, return JSON response
            if request.blueprint == 'api':
                return jsonify({'error': 'Authentication required'}), 401
            # For web requests, redirect to login
            return redirect(url_for('auth.login', next=request.url))
        
        try:
            # Verify the token and get user
            user = get_current_user_from_token(auth_token)
            if not user:
                session.pop('auth_token', None)
                if request.blueprint == 'api':
                    return jsonify({'error': 'Invalid token'}), 401
                return redirect(url_for('auth.login'))
            
            # Check if token is in active sessions
            user_session = UserSession.query.filter_by(
                token=auth_token,
                is_active=True
            ).first()
            
            if not user_session or user_session.expires_at < datetime.utcnow():
                session.pop('auth_token', None)
                if request.blueprint == 'api':
                    return jsonify({'error': 'Session expired'}), 401
                return redirect(url_for('auth.login'))
            
            # Set current user in flask.g
            g.current_user = user
            
            return f(*args, **kwargs)
            
        except jwt.InvalidTokenError:
            session.pop('auth_token', None)
            if request.blueprint == 'api':
                return jsonify({'error': 'Invalid token'}), 401
            return redirect(url_for('auth.login'))
            
    return decorated

def requires_roles(*roles):
    """Decorator for role-based access control"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_token = session.get('auth_token')
            if not auth_token:
                if request.blueprint == 'api':
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login', next=request.url))
            
            try:
                payload = jwt.decode(
                    auth_token,
                    current_app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
                
                if payload['role'] not in roles:
                    if request.blueprint == 'api':
                        return jsonify({'error': 'Insufficient permissions'}), 403
                    return redirect(url_for('web.index'))
                
                return f(*args, **kwargs)
                
            except jwt.InvalidTokenError:
                session.pop('auth_token', None)
                if request.blueprint == 'api':
                    return jsonify({'error': 'Invalid token'}), 401
                return redirect(url_for('auth.login', next=request.url))
                
        return decorated_function
    return decorator

def admin_required(f):
    """Shortcut decorator for admin-only routes"""
    @wraps(f)
    @requires_roles('admin')
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Helper function to get the current authenticated user"""
    auth_token = session.get('auth_token')
    if not auth_token:
        return None
        
    try:
        payload = jwt.decode(
            auth_token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return User.query.get(payload['user_id'])
    except jwt.InvalidTokenError:
        return None

def validate_token(token):
    """Helper function to validate a token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        
        user_session = UserSession.query.filter_by(
            token=token,
            is_active=True
        ).first()
        
        if not user_session or user_session.expires_at < datetime.utcnow():
            return None
            
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            return None
            
        return payload
        
    except jwt.InvalidTokenError:
        return None