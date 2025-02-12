from flask import Blueprint, request, session, current_app, render_template, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models import User, UserSession
from datetime import datetime
import jwt
from functools import wraps

auth = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_token = session.get('auth_token')
        if not auth_token:
            return redirect(url_for('auth.login'))
        
        try:
            payload = jwt.decode(auth_token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            if payload['role'] != 'admin':
                flash('Admin access required', 'error')
                return redirect(url_for('web.index'))
        except jwt.InvalidTokenError:
            session.pop('auth_token', None)
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Clear any existing session
    if 'auth_token' in session:
        return redirect(url_for('web.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html'), 400
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            if user:
                user.increment_failed_attempts()
            flash('Invalid username or password', 'error')
            return render_template('login.html'), 401
        
        if user.is_locked():
            flash('Account is locked due to too many failed attempts. Please try again later.', 'error')
            return render_template('login.html'), 401
        
        if not user.is_active:
            flash('Account is disabled. Please contact an administrator.', 'error')
            return render_template('login.html'), 401
        
        # Login successful
        user.reset_failed_attempts()
        auth_token = user.generate_auth_token()
        
        # Create session record
        UserSession.create_session(
            user=user,
            token=auth_token,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        session['auth_token'] = auth_token
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('web.index')
        return redirect(next_page)
        
    return render_template('login.html')

@auth.route('/logout')
def logout():
    auth_token = session.get('auth_token')
    if auth_token:
        user_session = UserSession.query.filter_by(token=auth_token).first()
        if user_session:
            user_session.deactivate()
        session.pop('auth_token', None)
    return redirect(url_for('auth.login'))

@auth.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard showing system overview."""
    from app.models import Article, DailySummary
    from datetime import datetime, timedelta
    
    # Get recent collection stats
    recent_time = datetime.utcnow() - timedelta(hours=24)
    articles_count = Article.query.filter(Article.published >= recent_time).count()
    latest_article = Article.query.order_by(Article.published.desc()).first()
    last_collection_time = latest_article.published if latest_article else None

    # Get summary stats
    summaries_count = DailySummary.query.filter_by(status='complete').count()
    latest_summary = DailySummary.query.filter_by(status='complete')\
        .order_by(DailySummary.generated_at.desc()).first()
    last_summary_time = latest_summary.generated_at if latest_summary else None
    
    return render_template('admin/dashboard.html',
        articles_count=articles_count,
        last_collection_time=last_collection_time,
        summaries_count=summaries_count,
        last_summary_time=last_summary_time
    )

@auth.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@auth.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        if not all([username, email, password]):
            flash('All fields are required', 'error')
            return render_template('admin/create_user.html'), 400
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('admin/create_user.html'), 400
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('admin/create_user.html'), 400
        
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('auth.admin_users'))
        
    return render_template('admin/create_user.html')

@auth.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        is_active = request.form.get('is_active') == 'on'
        new_password = request.form.get('password')
        
        if not all([username, email, role]):
            flash('Username, email and role are required', 'error')
            return render_template('admin/edit_user.html', user=user), 400
        
        username_exists = User.query.filter(
            User.username == username,
            User.id != user_id
        ).first()
        email_exists = User.query.filter(
            User.email == email,
            User.id != user_id
        ).first()
        
        if username_exists:
            flash('Username already exists', 'error')
            return render_template('admin/edit_user.html', user=user), 400
        if email_exists:
            flash('Email already exists', 'error')
            return render_template('admin/edit_user.html', user=user), 400
        
        user.username = username
        user.email = email
        user.role = role
        user.is_active = is_active
        
        if new_password:
            user.set_password(new_password)
            # Deactivate all user sessions on password change
            UserSession.query.filter_by(user_id=user.id).update({"is_active": False})
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('auth.admin_users'))
        
    return render_template('admin/edit_user.html', user=user)

@auth.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Don't allow deleting the last admin
    if user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last admin user', 'error')
        return redirect(url_for('auth.admin_users'))
    
    # Deactivate all sessions for this user
    UserSession.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('auth.admin_users'))

@auth.route('/sessions')
@admin_required
def list_sessions():
    """View active sessions (admin only)"""
    # Clean up expired sessions first
    UserSession.cleanup_expired()
    
    # Get all active sessions with user information
    sessions = UserSession.query.filter_by(is_active=True)\
        .join(User)\
        .add_columns(
            User.username,
            UserSession.id,
            UserSession.created_at,
            UserSession.expires_at,
            UserSession.ip_address,
            UserSession.user_agent
        ).all()
    
    return render_template('admin/sessions.html', sessions=sessions)

@auth.route('/sessions/<session_id>/revoke', methods=['POST'])
@admin_required
def revoke_session(session_id):
    """Revoke a specific session"""
    user_session = UserSession.query.get_or_404(session_id)
    user_session.deactivate()
    
    flash('Session revoked successfully', 'success')
    return redirect(url_for('auth.list_sessions'))