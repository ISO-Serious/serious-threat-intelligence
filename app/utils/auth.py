from functools import wraps
from flask import session, redirect, url_for, request, jsonify, current_app
from app.models import User, UserSession
import jwt
from datetime import datetime

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Keep the email2 endpoint public as per existing code
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
            # Verify the token
            payload = jwt.decode(
                auth_token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # Check if token is in active sessions
            user_session = UserSession.query.filter_by(
                token=auth_token,
                is_active=True
            ).first()
            
            if not user_session or user_session.expires_at < datetime.utcnow():
                session.pop('auth_token', None)
                if request.blueprint == 'api':
                    return jsonify({'error': 'Session expired'}), 401
                return redirect(url_for('auth.login', next=request.url))
            
            # Check if user is still active
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                session.pop('auth_token', None)
                if request.blueprint == 'api':
                    return jsonify({'error': 'Account disabled'}), 401
                return redirect(url_for('auth.login'))
            
            # Store user info in g for access in views
            from flask import g
            g.current_user = user
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            session.pop('auth_token', None)
            if request.blueprint == 'api':
                return jsonify({'error': 'Token expired'}), 401
            return redirect(url_for('auth.login', next=request.url))
            
        except jwt.InvalidTokenError:
            session.pop('auth_token', None)
            if request.blueprint == 'api':
                return jsonify({'error': 'Invalid token'}), 401
            return redirect(url_for('auth.login', next=request.url))
            
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