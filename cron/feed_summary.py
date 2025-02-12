from datetime import datetime, timezone, timedelta
import logging
import anthropic
import json
import os
from pathlib import Path
import argparse
from prompts import ARTICLE_SUMMARY_PROMPT
from db_helper import get_db
from app.models import Feed, Article, DailySummary
import time

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
Title: {article.title}
URL: {article.url}
Author: {article.author or 'Unknown'}
Summary: {article.summary}
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
            
            response_text = response.content[0].text
            
            try:
                summary_dict = json.loads(response_text)
                logger.info(f"Successfully parsed summary for {category}")
                return summary_dict
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response for {category}: {str(e)}")
                logger.error(f"Raw text: {response_text[:200]}...")
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
    def __init__(self, summarizer: ArticleSummarizer):
        self.summarizer = summarizer
        self.app, self.db = get_db()
        self.app.app_context().push()

    def cleanup_old_articles(self):
        """Delete articles that are older than 3 days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=3)
            old_articles = Article.query.filter(Article.published < cutoff_date).all()
            
            if old_articles:
                count = len(old_articles)
                for article in old_articles:
                    self.db.session.delete(article)
                
                self.db.session.commit()
                logger.info(f"Successfully deleted {count} articles older than 3 days")
            else:
                logger.info("No articles found older than 3 days")
                
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {str(e)}")
            self.db.session.rollback()
            raise

    def generate_daily_summary(self) -> dict:
        try:
            # Clean up old articles before generating new summary
            self.cleanup_old_articles()
            
            today = datetime.now(timezone.utc).date().isoformat()
            twelve_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            
            # Now both date and generated_at are compared as strings
            existing_summary = DailySummary.query.filter(
                DailySummary.date == today,
                DailySummary.generated_at > twelve_hours_ago,
                DailySummary.status == 'complete'
            ).first()
            
            if existing_summary:
                return json.loads(existing_summary.summary)
            
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            articles = Article.query.join(Feed).filter(
                Article.published > yesterday
            ).order_by(Feed.category, Article.published.desc()).all()
            
            categorized_articles = {}
            for article in articles:
                category = article.feed.category
                if category not in categorized_articles:
                    categorized_articles[category] = []
                categorized_articles[category].append(article)
            
            summary_content = {}
            for category, articles in categorized_articles.items():
                summary_content[category] = self.summarizer.generate_summary(
                    articles, category
                )
            
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Store everything as strings
            new_summary = DailySummary(
                date=today,
                summary=json.dumps(summary_content, ensure_ascii=False),
                generated_at=current_time,
                status='complete'
            )
            
            self.db.session.add(new_summary)
            self.db.session.commit()
            
            return summary_content
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {str(e)}")
            self.db.session.rollback()
            raise

def main():
    """Main entry point for generating the daily feed summary."""
    parser = argparse.ArgumentParser(description='RSS Feed Summarizer')
    
    parser.add_argument('--api-key', required=False,
                       help='Claude API key for generating summaries')
    parser.add_argument('--interval', type=int, default=86400,
                       help='Run interval in seconds (default: 86400 for 24 hours)')
    parser.add_argument('--cron', action='store_true',
                       help='Run once and exit (for cron jobs)')
    
    args = parser.parse_args()
    
    try:
        while True:
            api_key = os.getenv('CLAUDE_API_KEY') or args.api_key
            if not api_key:
                raise ValueError("API key not found in CLAUDE_API_KEY environment variable or --api-key argument")
                
            summarizer = ArticleSummarizer(api_key=api_key)
            feed_summarizer = FeedSummarizer(summarizer)
            summary = feed_summarizer.generate_daily_summary()
            
            if args.cron:
                logger.info("Running in cron mode - exiting after single execution")
                break
                
            logger.info(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Summary generation stopped by user")
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()