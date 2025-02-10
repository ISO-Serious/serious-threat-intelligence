from flask import Blueprint, render_template, request, url_for, session, redirect, Response, current_app

auth = Blueprint('auth', __name__)

def check_auth(username, password):
    return username == current_app.config['AUTH_USERNAME'] and password == current_app.config['AUTH_PASSWORD']

def authenticate():
    return Response(
        'Could not verify access level.\n'
        'Login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if check_auth(request.form['username'], request.form['password']):
            session['authenticated'] = True
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('web.index'))
        return 'Invalid credentials', 401
    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('auth.login'))