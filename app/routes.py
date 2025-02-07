from flask import Blueprint, jsonify, render_template, current_app
from datetime import datetime
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

def normalize_json_string(s):
    """Normalize a JSON string to handle escapes and control characters."""
    # Common replacements to handle
    replacements = [
        ('\\\\n', '\n'),      # Double-escaped newlines
        ('\\\\"', '"'),       # Double-escaped quotes
        ('\\\\\'', "'"),      # Double-escaped single quotes
        ('\\n', '\n'),        # Single-escaped newlines
        ('\\"', '"'),         # Single-escaped quotes
        ('\\\'', "'"),        # Single-escaped single quotes
        ('\\\\', '\\')        # Double-escaped backslashes
    ]
    
    # Apply replacements
    for old, new in replacements:
        s = s.replace(old, new)
    
    return s

def parse_double_encoded_json(s):
    """Parse JSON that has been encoded twice."""
    try:
        # First parse - get the outer JSON structure
        outer = json.loads(s)
        
        # For each section, parse the inner JSON string
        result = {}
        for key, value in outer.items():
            try:
                if isinstance(value, str):
                    # First normalize the string
                    normalized = normalize_json_string(value)
                    # Then parse it
                    parsed = json.loads(normalized)
                    # Clean up any remaining escapes in text fields
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
                # Return raw data for debugging
                return {
                    'summary': json.loads(result[0]),
                    'date': result[1],
                    'generated_at': result[2]
                }
        return None
        
    except Exception as e:
        logger.error(f"Error in get_latest_summary: {str(e)}")
        raise
    finally:
        conn.close()

@main.route('/summary')
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
    """Endpoint to retrieve the most recent daily summary as formatted HTML."""
    try:
        result = get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
            
            return render_template(
                'email/summary.html',
                summary=result['summary'],
                date=date_str
            )
        else:
            return "No recent summaries found in the database", 404
            
    except Exception as e:
        logger.error(f"Error generating email view: {str(e)}")
        return f"Error generating email view: {str(e)} (PATH: {current_app.config['DATABASE_PATH']})", 500
    
@main.route('/email2')
def get_email2():
    """Endpoint to retrieve the most recent daily summary as formatted HTML for email clients."""
    try:
        result = get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
            
            return render_template(
                'email2/email.html',
                summary=result['summary'],
                date=date_str
            )
        else:
            return "No recent summaries found in the database", 404
            
    except Exception as e:
        logger.error(f"Error generating email2 view: {str(e)}")
        return f"Error generating email view: {str(e)}", 500    

@main.route('/debug')
def debug_view():
    """Debug endpoint to see the data structure."""
    try:
        result = get_latest_summary(current_app.config['DATABASE_PATH'])
        if result:
            output = ["=== Summary Structure ===\n"]
            for category, content in result['summary'].items():
                output.append(f"\n=== {category} ===")
                if isinstance(content, dict):
                    output.append(f"Section Title: {content.get('section_title', 'N/A')}")
                    tasks = content.get('actionable_tasks', [])
                    output.append(f"Number of Tasks: {len(tasks)}")
                    if len(tasks) > 0:
                        output.append("\nFirst Task:")
                        output.append(json.dumps(tasks[0], indent=2))
                    output.append(f"\nSummary Preview: {content.get('summary', '')[:200]}...")
                else:
                    output.append(f"Content type: {type(content)}")
                    output.append(f"Content preview: {str(content)[:200]}")
            
            return f"<pre>{''.join(output)}</pre>"
        return "No data found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500
    
@main.route('/')
def index():
    """Simple health check endpoint for monitoring."""
    return "Hello World", 200    

@main.route('/health')
def health_check():
    """Simple health check endpoint for monitoring."""
    return "OK", 200