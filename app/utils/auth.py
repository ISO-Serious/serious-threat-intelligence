from functools import wraps
from flask import session, redirect, url_for, request

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.endpoint == 'web.email2':
            return f(*args, **kwargs)
            
        if not session.get('authenticated'):
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated