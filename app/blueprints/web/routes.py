from flask import Blueprint, render_template, request, current_app
from datetime import datetime
from app.utils.database import get_all_summary_dates, get_latest_summary, get_summary_by_id, get_recent_articles
from app.utils.auth import requires_auth
import logging
import re

logger = logging.getLogger(__name__)
web = Blueprint('web', __name__)

def strip_html(text):
    return re.sub('<[^<]+?>', '', text)

@web.route('/')
def index():
    return "Hello World", 200

@web.route('/health')
def health_check():
    return "OK", 200

@web.route('/list-emails')
@requires_auth
def list_emails():
    try:
        summaries = get_all_summary_dates(current_app.config['DATABASE_PATH'])
        articles = get_recent_articles(current_app.config['DATABASE_PATH'])
        return render_template(
            'email/list.html',
            summaries=[(id, datetime.fromisoformat(date).strftime('%A, %B %d, %Y')) 
                      for id, date in summaries],
            articles=[(article[0], article[1], article[2], strip_html(article[3]), 
                      datetime.fromisoformat(str(article[4])).strftime('%B %d, %Y'))
                     for article in articles]
        )
    except Exception as e:
        logger.error(f"Error listing summaries: {str(e)}")
        return f"Error listing summaries: {str(e)}", 500

@web.route('/email')
@requires_auth
def get_email():
    try:
        summary_id = request.args.get('id')
        result = get_summary_by_id(current_app.config['DATABASE_PATH'], summary_id) if summary_id else get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
            return render_template('email/summary.html', summary=result['summary'], date=date_str)
        return "Summary not found", 404
            
    except Exception as e:
        logger.error(f"Error generating email view: {str(e)}")
        return f"Error generating email view: {str(e)}", 500

@web.route('/email2')
def get_email2():
    try:
        summary_id = request.args.get('id')
        result = get_summary_by_id(current_app.config['DATABASE_PATH'], summary_id) if summary_id else get_latest_summary(current_app.config['DATABASE_PATH'])
        
        if result:
            date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
            return render_template('email2/email.html', summary=result['summary'], date=date_str)
        return "Summary not found", 404
            
    except Exception as e:
        logger.error(f"Error generating email2 view: {str(e)}")
        return f"Error generating email view: {str(e)}", 500