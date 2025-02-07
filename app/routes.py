from flask import Blueprint, jsonify, render_template, current_app, request, url_for, session, redirect
from functools import wraps
from flask import Response
import base64
from datetime import datetime
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

def check_auth(username, password):
    """Verify credentials against expected values."""
    return username == current_app.config['AUTH_USERNAME'] and password == current_app.config['AUTH_PASSWORD']

def authenticate():
    """Send 401 response that enables basic auth."""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.endpoint == 'main.email2':
            return f(*args, **kwargs)
            
        if not session.get('authenticated'):
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def normalize_json_string(s):
    """Normalize a JSON string to handle escapes and control characters."""
    replacements = [
        ('\\\\n', '\n'),
        ('\\\\"', '"'),
        ('\\\\\'', "'"),
        ('\\n', '\n'),
        ('\\"', '"'),
        ('\\\'', "'"),
        ('\\\\', '\\')
    ]
    
    for old, new in replacements:
        s = s.replace(old, new)
    
    return s

def parse_double_encoded_json(s):
    """Parse JSON that has been encoded twice."""
    try:
        outer = json.loads(s)
        result = {}
        for key, value in outer.items():
            try:
                if isinstance(value, str):
                    normalized = normalize_json_string(value)
                    parsed = json.loads(normalized)
                    if isinstance(parsed, dict):
                        if 'summary' in parsed:
                            parsed['summary'] = normalize_json_string(parsed['summary'])
                        if 'actionable_tasks' in parsed:
                            for task in parsed['actionable_tasks']:
                                if 'description' in task:
                                    task['description'] = normalize_json_string(task['description'])
                    result[key] = parsed
                else:
                    result[key] = value
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing inner JSON for {key}: {str(e)}")
                logger.error(f"Value: {value[:200]}")
                result[key] = value
                
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing outer JSON: {str(e)}")
        return {}

def get_latest_summary(db_path):
    """Helper method to retrieve the latest summary from the database."""
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        result = c.execute('''
            SELECT summary, date, generated_at 
            FROM daily_summaries 
            WHERE status = 'complete'
            ORDER BY generated_at DESC 
            LIMIT 1
        ''').fetchone()
        
        if result:
            try:
                parsed_summary = parse_double_encoded_json(result[0])
                return {
                    'summary': parsed_summary,
                    'date': result[1],
                    'generated_at': result[2]
                }
            except Exception as e:
                logger.error(f"Error parsing summary: {str(e)}")
                return {
                    'summary': json.loads(result[0]),
                    'date': result[1],
                    'generated_at': result[2]
                }
        return None
    finally:
        conn.close()

def get_summary_by_id(db_path, summary_id):
    """Helper method to retrieve a specific summary from the database."""
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        result = c.execute('''
            SELECT summary, date, generated_at 
            FROM daily_summaries 
            WHERE id = ? AND status = 'complete'
        ''', (summary_id,)).fetchone()
        
        if result:
            parsed_summary = parse_double_encoded_json(result[0])
            return {
                'summary': parsed_summary,
                'date': result[1],
                'generated_at': result[2]
            }
        return None
    finally:
        conn.close()

def get_all_summary_dates(db_path):
    """Helper method to retrieve all summary dates and IDs."""
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        results = c.execute('''
            SELECT id, date 
            FROM daily_summaries 
            WHERE status = 'complete'
            ORDER BY date DESC
        ''').fetchall()
        return results
    finally:
        conn.close()

@main.route('/list-emails')
@requires_auth
def list_emails():
    """Endpoint to list all available summary dates."""
    try:
        summaries = get_all_summary_dates(current_app.config['DATABASE_PATH'])
        return render_template(
            'email/list.html',
            summaries=[(id, datetime.fromisoformat(date).strftime('%A, %B %d, %Y')) 
                      for id, date in summaries]
        )
    except Exception as e:
        logger.error(f"Error listing summaries: {str(e)}")
        return f"Error listing summaries: {str(e)}", 500

@main.route('/summary')
@requires_auth
def get_summary():
    """Endpoint to retrieve the most recent daily summary as JSON."""
    try:
        result = get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            return jsonify(result['summary'])
        else:
            return jsonify({
                "error": "No summary available",
                "message": "No recent summaries found in the database"
            }), 404
            
    except Exception as e:
        logger.error(f"Error retrieving summary: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve summary",
            "message": str(e)
        }), 500

@main.route('/email')
def get_email():
    """Endpoint to retrieve a specific summary as formatted HTML."""
    try:
        summary_id = request.args.get('id')
        if summary_id:
            result = get_summary_by_id(current_app.config['DATABASE_PATH'], summary_id)
        else:
            result = get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
            return render_template(
                'email/summary.html',
                summary=result['summary'],
                date=date_str
            )
        else:
            return "Summary not found", 404
            
    except Exception as e:
        logger.error(f"Error generating email view: {str(e)}")
        return f"Error generating email view: {str(e)}", 500

@main.route('/email2')
def get_email2():
    """Endpoint to retrieve the most recent daily summary as formatted HTML for email clients."""
    try:
        summary_id = request.args.get('id')
        if summary_id:
            result = get_summary_by_id(current_app.config['DATABASE_PATH'], summary_id)
        else:
            result = get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
            return render_template(
                'email/summary.html',
                summary=result['summary'],
                date=date_str
            )
        else:
            return "Summary not found", 404
            
    except Exception as e:
        logger.error(f"Error generating email2 view: {str(e)}")
        return f"Error generating email view: {str(e)}", 500    
    
@main.route('/delete-summary/<int:summary_id>', methods=['DELETE'])
@requires_auth
def delete_summary(summary_id):
    """Delete a specific summary from the database."""
    try:
        conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
        c = conn.cursor()
        c.execute('DELETE FROM daily_summaries WHERE id = ?', (summary_id,))
        conn.commit()
        conn.close()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting summary {summary_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form['username'] == current_app.config['AUTH_USERNAME'] and 
            request.form['password'] == current_app.config['AUTH_PASSWORD']):
            session['authenticated'] = True
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.index'))
        return 'Invalid credentials', 401
        
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('main.login'))    

@main.route('/')
def index():
    """Simple index page."""
    return "Hello World", 200    

@main.route('/health')
def health_check():
    """Simple health check endpoint for monitoring."""
    return "OK", 200