from datetime import datetime, timezone, timedelta
import sqlite3
import logging
import anthropic
import json
import re
import os
from pathlib import Path
import argparse
from prompts import ARTICLE_SUMMARY_PROMPT

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feed_summary.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure SQLite to properly handle datetime objects
def adapt_datetime(dt):
    """Convert datetime objects to SQLite TEXT format."""
    return dt.isoformat()

def convert_datetime(text):
    """Convert SQLite TEXT format back to datetime objects."""
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return text

# Register the datetime adapters with SQLite
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

class ArticleSummarizer:
    def __init__(self, api_key):
        self.client = anthropic.Anthropic(
            api_key=api_key
        )

    def generate_summary(self, articles, category):
        if not articles:
            return {
                "section_title": "No Summary Available",
                "summary": "No articles to summarize for this category.",
                "actionable_tasks": []
            }
        
        article_texts = []
        for article in articles[:20]:
            article_text = f"""
Title: {article['title']}
URL: {article['url']}
Author: {article.get('author', 'Unknown')}
Summary: {article['summary']}
            """
            article_texts.append(article_text)
        
        prompt = ARTICLE_SUMMARY_PROMPT.format(
            category=category,
            articles=chr(10).join(article_texts)
        )

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0,
                system="You are a skilled journalist writing clear, informative summaries for a news digest email.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Get the response content directly from the TextBlock
            response_text = response.content[0].text
            
            # Parse the JSON
            try:
                summary_dict = json.loads(response_text)
                logger.info(f"Successfully parsed summary for {category}")
                return summary_dict
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response for {category}: {str(e)}")
                logger.error(f"Raw text: {response_text[:200]}...")
                # Return structured error response
                return {
                    "section_title": f"Error Processing {category}",
                    "summary": "Error parsing AI-generated summary. Please check the original articles.",
                    "actionable_tasks": []
                }

        except Exception as e:
            logger.error(f"Error generating summary for {category}: {str(e)}")
            return {
                "section_title": f"Error in {category}",
                "summary": f"Error generating AI summary for {category}. Please check the original articles.",
                "actionable_tasks": []
            }

class FeedSummarizer:
    def __init__(self, db_path: str, summarizer: ArticleSummarizer):
        self.db_path = db_path
        self.summarizer = summarizer
        
        if not Path(db_path).exists():
            raise FileNotFoundError(
                f"Database not found at {db_path}. Please run the setup.py script first."
            )

    def generate_daily_summary(self) -> dict:
        """Generate an AI-powered summary of articles from the past 24 hours."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            
            today = datetime.now(timezone.utc).date()
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            
            # Use json() function to properly extract JSON data
            existing_summary = c.execute('''
                SELECT json(summary) FROM daily_summaries
                WHERE date = ? AND generated_at > ?
                AND status = 'complete'
            ''', (today.isoformat(), (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat())).fetchone()
            
            if existing_summary:
                # Result is already parsed JSON due to json() function
                return existing_summary[0]
            
            articles = c.execute('''
                SELECT 
                    f.category,
                    a.title,
                    a.url,
                    a.published,
                    COALESCE(NULLIF(a.summary, ''), a.content, 'No content available') as content,
                    a.author
                FROM articles a
                JOIN feeds f ON a.feed_id = f.id
                WHERE a.published > ?
                ORDER BY f.category, a.published DESC
            ''', (yesterday,)).fetchall()
            
            categorized_articles = {}
            for category, title, url, published, content, author in articles:
                if category not in categorized_articles:
                    categorized_articles[category] = []
                
                categorized_articles[category].append({
                    'title': title,
                    'url': url,
                    'published': published,
                    'summary': content,
                    'author': author
                })
            
            summary_content = {}
            for category, articles in categorized_articles.items():
                summary_content[category] = self.summarizer.generate_summary(
                    articles, category
                )
            
            current_time = datetime.now(timezone.utc)
            
            # Store the summary as proper JSON using json() function
            c.execute('''
                INSERT INTO daily_summaries (date, summary, generated_at, status)
                VALUES (?, json(?), ?, ?)
            ''', (
                today.isoformat(),
                json.dumps(summary_content, ensure_ascii=False),
                current_time.isoformat(),
                'complete'
            ))
            
            conn.commit()
            return summary_content
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {str(e)}")
            if conn:
                conn.rollback()
            raise
            
        finally:
            if conn:
                conn.close()

def main():
    """Main entry point for generating the daily feed summary."""
    parser = argparse.ArgumentParser(description='RSS Feed Summarizer')
    
    parser.add_argument('--db', default='../rss_feeds.db',
                       help='Database file path (default: rss_feeds.db)')
    parser.add_argument('--api-key', required=False,
                       help='Claude API key for generating summaries')
    
    args = parser.parse_args()
    
    try:
        db_path = os.getenv('DATABASE_PATH') or args.db
        api_key = os.getenv('CLAUDE_API_KEY') or args.api_key
        if not api_key:
            raise ValueError("API key not found in CLAUDE_API_KEY environment variable or --api-key argument")
            
        summarizer = ArticleSummarizer(api_key=api_key)
        feed_summarizer = FeedSummarizer(db_path, summarizer)
        summary = feed_summarizer.generate_daily_summary()
        
        # Print summary to stdout for potential piping to other processes
        # print(json.dumps(summary, indent=2))
        
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()