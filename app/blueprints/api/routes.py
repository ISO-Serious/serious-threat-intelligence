from flask import Blueprint, jsonify, current_app, request
import os
from app.extensions import db
from app.models import Article, DailySummary
from app.utils.process import run_script_async
from app.utils.database import get_latest_summary, get_summary_by_id
from app.utils.json import parse_double_encoded_json
from app.utils.auth import requires_auth
import logging
import json


logger = logging.getLogger(__name__)
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/collect-feeds', methods=['POST'])
@requires_auth
def collect_feeds():
    try:
        if not os.getenv('DATABASE_URL'):
            return jsonify({'status': 'error', 'message': 'DATABASE_URL not set'}), 500
            
        script_path = os.path.join(current_app.root_path, '..', 'cron', 'feed_collector.py')
        pid = run_script_async(script_path, ['--cron'])
        return jsonify({'status': 'success', 'process_id': pid}), 202
        
    except Exception as e:
        logger.error(f"Failed to start feed collection: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api.route('/generate-summary', methods=['POST'])
@requires_auth
def generate_summary():
    try:
        if not os.getenv('DATABASE_URL') or not os.getenv('CLAUDE_API_KEY'):
            return jsonify({'status': 'error', 'message': 'Required env vars not set'}), 500
            
        script_path = os.path.join(current_app.root_path, '..', 'cron', 'feed_summary.py')
        pid = run_script_async(script_path, ['--cron'])
        return jsonify({'status': 'success', 'process_id': pid}), 202
        
    except Exception as e:
        logger.error(f"Failed to start summary generation: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api.route('/check-process/<int:pid>', methods=['GET'])
@requires_auth
def check_process(pid):
    try:
        os.kill(pid, 0)
        return jsonify({'status': 'running', 'process_id': pid})
    except OSError:
        return jsonify({'status': 'completed', 'process_id': pid})

@api.route('/summary')
@requires_auth
def get_summary():
    try:
        result = get_latest_summary()
        if result:
            return jsonify(result['summary'])
        return jsonify({"error": "No summary available"}), 404
    except Exception as e:
        logger.error(f"Error retrieving summary: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api.route('/summary/<int:summary_id>', methods=['DELETE'])
@requires_auth
def delete_summary(summary_id):
    try:
        summary = DailySummary.query.get_or_404(summary_id)
        db.session.delete(summary)
        db.session.commit()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting summary {summary_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@api.route('/article/<int:id>', methods=['DELETE'])
@requires_auth
def delete_article(id):
    try:
        article = Article.query.get_or_404(id)
        db.session.delete(article)
        db.session.commit()
        return "", 204
    except Exception as e:
        logger.error(f"Error deleting article: {str(e)}")
        return f"Error deleting article: {str(e)}", 500
    
@api.route('/summary/<int:summary_id>/task', methods=['DELETE'])
@requires_auth
def delete_task(summary_id):
    category = request.args.get('category')
    task_index = request.args.get('task_index', type=int)
    
    if category is None or task_index is None:
        return jsonify({"error": "Category and task_index are required"}), 400

    try:
        summary = DailySummary.query.filter_by(id=summary_id, status='complete').first()
        if not summary:
            return jsonify({"error": "Summary not found"}), 404
            
        try:
            if isinstance(summary.summary, str):
                summary_data = parse_double_encoded_json(summary.summary)
            else:
                summary_data = summary.summary
        except Exception as e:
            logger.error(f"Error parsing summary: {str(e)}")
            return jsonify({"error": "Error parsing summary"}), 500
            
        if category not in summary_data or 'actionable_tasks' not in summary_data[category]:
            return jsonify({"error": "Category not found or no tasks available"}), 404
            
        if task_index < 0 or task_index >= len(summary_data[category]['actionable_tasks']):
            return jsonify({"error": "Task index out of range"}), 400
            
        del summary_data[category]['actionable_tasks'][task_index]
        summary.summary = json.dumps(summary_data)
        
        db.session.commit()
        return '', 204
            
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@api.route('/summary/<int:summary_id>/commentary', methods=['POST'])
@requires_auth
def update_commentary(summary_id):
    try:
        logger.info(f"Received request to update commentary for summary {summary_id}")
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        logger.info(f"Received data: {data}")
        
        if not isinstance(data, dict) or 'commentary' not in data:
            logger.error("Invalid data format or missing commentary field")
            return jsonify({"error": "Commentary field is required"}), 400
            
        summary = DailySummary.query.get_or_404(summary_id)
        logger.info(f"Found summary with ID {summary_id}")
        
        summary.commentary = data['commentary']
        logger.info(f"Set commentary to: {data['commentary']}")
        
        db.session.commit()
        logger.info("Successfully committed to database")
        
        return jsonify({
            "status": "success",
            "commentary": summary.commentary
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating commentary: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@api.route('/markdown-preview', methods=['POST'])
@requires_auth
def markdown_preview():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        if 'text' not in data:
            return jsonify({"error": "Text field is required"}), 400
            
        # Use the same markdown filter from __init__.py
        html = current_app.jinja_env.filters['markdown'](data['text'])
        
        return jsonify({
            "html": html
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating markdown preview: {str(e)}")
        return jsonify({"error": str(e)}), 500