from flask import Blueprint, jsonify, current_app
import os
import sqlite3
from app.utils.process import run_script_async
from app.utils.database import get_latest_summary, get_summary_by_id
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