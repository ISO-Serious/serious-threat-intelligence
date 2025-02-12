from ..extensions import db
from ..models import Article, DailySummary
from .json import parse_double_encoded_json
import logging
import json

logger = logging.getLogger(__name__)

def get_latest_summary():
    result = DailySummary.query.filter_by(status='complete', summary_type='weekly')\
        .order_by(DailySummary.generated_at.desc())\
        .first()
    
    if result:
        try:
            summary = result.summary if isinstance(result.summary, dict) else parse_double_encoded_json(result.summary)
            return {
                'summary': json.dumps(summary),
                'date': result.date,
                'generated_at': result.generated_at,
                'commentary': result.commentary,
                'summary_type': result.summary_type
            }
        except Exception as e:
            logger.error(f"Error parsing summary: {str(e)}")
            return {
                'summary': json.dumps(result.summary),
                'date': result.date,
                'generated_at': result.generated_at,
                'commentary': result.commentary,
                'summary_type': result.summary_type
            }
    return None

def get_summary_by_id(summary_id):
    result = DailySummary.query.filter_by(id=summary_id, status='complete').first()
    
    if result:
        try:
            summary = result.summary if isinstance(result.summary, dict) else parse_double_encoded_json(result.summary)
            return {
                'summary': json.dumps(summary),
                'date': result.date,
                'generated_at': result.generated_at,
                'commentary': result.commentary,
                'summary_type': result.summary_type
            }
        except Exception as e:
            logger.error(f"Error parsing summary: {str(e)}")
            return {
                'summary': json.dumps(result.summary),
                'date': result.date,
                'generated_at': result.generated_at,
                'commentary': result.commentary,
                'summary_type': result.summary_type
            }
    return None

def get_all_summary_dates():
    results = DailySummary.query.filter_by(status='complete')\
        .order_by(DailySummary.date.desc())\
        .add_columns(
            DailySummary.id,
            DailySummary.date,
            DailySummary.summary_type,
            DailySummary.commentary
        )\
        .all()
    
    return [(row[1], row[2], row[3], row[4]) for row in results]

def get_recent_articles(limit=50):
    articles = Article.query\
        .order_by(Article.published.desc())\
        .limit(limit)\
        .all()
    
    return [(
        article.id,
        article.title,
        article.url,
        article.summary,
        article.published
    ) for article in articles]