from flask import Blueprint, render_template, request, current_app
from datetime import datetime
from app.utils.database import get_all_summary_dates, get_latest_summary, get_summary_by_id, get_recent_articles
from app.utils.auth import requires_auth
import logging
import re
import json

logger = logging.getLogger(__name__)
web = Blueprint('web', __name__)

def strip_html(text):
    return re.sub('<[^<]+?>', '', text)

def get_formatted_summary(summary_id=None):
    """Helper function to get and format summary data.
    
    Args:
        summary_id: Optional ID of specific summary to retrieve
        
    Returns:
        tuple: (formatted_data, status_code, error_message)
            formatted_data: dict with summary data or None
            status_code: HTTP status code
            error_message: Error message string or None
    """
    try:
        result = get_summary_by_id(summary_id) if summary_id else get_latest_summary()
        
        if not result:
            return None, 404, "Summary not found"
            
        date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
        summary_dict = json.loads(result['summary'])
        
        formatted_data = {
            'summary': summary_dict,
            'date': date_str,
            'commentary': result.get('commentary'),
            'summary_type': result.get('summary_type')
        }
        
        return formatted_data, 200, None
        
    except Exception as e:
        logger.error(f"Error retrieving summary: {str(e)}")
        logger.exception(e)  # Log full stack trace
        return None, 500, f"Error generating email view: {str(e)}"

@web.route('/')
def index():
    summary_id = request.args.get('id')
    data, status_code, error = get_formatted_summary(summary_id)
    
    if error:
        return error, status_code
        
    return render_template('web-formatted-email/index-no-edit.html', **data)

@web.route('/email')
def web_formatted_email():
    summary_id = request.args.get('id')
    data, status_code, error = get_formatted_summary(summary_id)
    
    if error:
        return error, status_code
        
    return render_template('web-formatted-email/index.html', **data)

def get_formatted_email_response(summary_type='weekly'):
    """
    Helper function to handle formatted email requests for both weekly and daily summaries.
    
    Args:
        summary_type (str): Type of summary to retrieve ('weekly' or 'daily')
        
    Returns:
        tuple: Contains either (rendered template, status_code) or (error message, status_code)
    """
    try:
        summary_id = request.args.get('id')
        result = get_summary_by_id(summary_id) if summary_id else get_latest_summary(summary_type)
        
        if not result:
            return "Summary not found", 404
            
        date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
        summary_dict = json.loads(result['summary'])
        
        return render_template(
            'mail-client-formatted-email/email.html',
            summary=summary_dict,
            date=date_str,
            commentary=result.get('commentary'),
            summary_type=result.get('summary_type')
        ), 200
            
    except Exception as e:
        error_msg = f"Error generating email view: {str(e)}"
        logger.error(error_msg)
        return error_msg, 500

@web.route('/email/mail-client-formatted')
def mail_client_formatted_weekly():
    """Route for weekly formatted emails (default)"""
    return get_formatted_email_response()

@web.route('/email/mail-client-formatted/daily')
def mail_client_formatted_daily():
    """Route for daily formatted emails"""
    return get_formatted_email_response('daily')
    
@web.route('/health')
def health_check():
    return "OK", 200