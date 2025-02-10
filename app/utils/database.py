import sqlite3
from .json import parse_double_encoded_json
import logging

logger = logging.getLogger(__name__)

def get_latest_summary(db_path):
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

def get_recent_articles(db_path, limit=50):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    articles = c.execute('''
        SELECT a.id, a.title, a.url, a.summary, a.published
        FROM articles a
        ORDER BY a.published DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return articles