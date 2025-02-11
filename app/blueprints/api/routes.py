from flask import Blueprint, jsonify, current_app, request
import os
import sqlite3
import json
from app.utils.process import run_script_async
from app.utils.database import get_latest_summary, get_summary_by_id, parse_double_encoded_json
from app.utils.auth import requires_auth
import logging

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/collect-feeds', methods=['POST'])
@requires_auth
def collect_feeds():
    try:
        if not os.getenv('DATABASE_PATH'):
            return jsonify({'status': 'error', 'message': 'DATABASE_PATH not set'}), 500
            
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
        if not os.getenv('DATABASE_PATH') or not os.getenv('CLAUDE_API_KEY'):
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
        result = get_latest_summary(current_app.config['DATABASE_PATH'])
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
        conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
        c = conn.cursor()
        c.execute('DELETE FROM daily_summaries WHERE id = ?', (summary_id,))
        conn.commit()
        conn.close()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting summary {summary_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@api.route('/article/<int:id>', methods=['DELETE'])
@requires_auth
def delete_article(id):
    try:
        conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
        c = conn.cursor()
        
        # Check if article exists
        article = c.execute('SELECT id FROM articles WHERE id = ?', (id,)).fetchone()
        if not article:
            conn.close()
            return "Article not found", 404
            
        c.execute('DELETE FROM articles WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return "", 204
    except Exception as e:
        logger.error(f"Error deleting article: {str(e)}")
        return f"Error deleting article: {str(e)}", 500
    
@api.route('/summary/<int:summary_id>/task', methods=['DELETE'])
@requires_auth
def delete_task(summary_id):
    # Validate input parameters first
    category = request.args.get('category')
    task_index = request.args.get('task_index', type=int)
    
    if category is None or task_index is None:
        return jsonify({"error": "Category and task_index are required"}), 400

    conn = None    
    try:
        # Establish database connection
        conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
        c = conn.cursor()
        
        # Get the current summary
        result = c.execute('''
            SELECT summary
            FROM daily_summaries 
            WHERE id = ? AND status = 'complete'
        ''', (summary_id,)).fetchone()
        
        if not result:
            if conn:
                conn.close()
            return jsonify({"error": "Summary not found"}), 404
            
        # Parse the summary JSON
        try:
            summary = parse_double_encoded_json(result[0])
        except Exception as e:
            logger.error(f"Error parsing summary: {str(e)}")
            if conn:
                conn.close()
            return jsonify({"error": "Error parsing summary"}), 500
            
        # Remove the task
        if category not in summary or 'actionable_tasks' not in summary[category]:
            if conn:
                conn.close()
            return jsonify({"error": "Category not found or no tasks available"}), 404
            
        if task_index < 0 or task_index >= len(summary[category]['actionable_tasks']):
            if conn:
                conn.close()
            return jsonify({"error": "Task index out of range"}), 400
            
        # Delete the task and update the database
        del summary[category]['actionable_tasks'][task_index]
        
        c.execute('''
            UPDATE daily_summaries
            SET summary = ?
            WHERE id = ?
        ''', (json.dumps(summary), summary_id))
        
        conn.commit()
        conn.close()
        return '', 204
            
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500