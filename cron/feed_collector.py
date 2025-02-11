import feedparser
from datetime import datetime, timezone
import time
import html
import logging
import os
from pathlib import Path
import argparse
from db_helper import get_db, Feed, Article

# Configure feedparser to use the newer date handler
feedparser.datetimes.registerDateHandler(lambda date_string: datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feed_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FeedCollector:
    """Handles fetching and storing RSS feeds in the database."""
    
    def __init__(self):
        """Initialize the feed collector."""
        self.app, self.db = get_db()
        self.app.app_context().push()
    
    def collect_articles(self):
        """Fetch articles from all active feeds and store them in the database."""
        try:
            # Get all active feeds from the database
            feeds = Feed.query.filter_by(active=True).all()
            
            for feed in feeds:
                logger.info(f"Fetching articles from {feed.name}")
                current_time = datetime.now(timezone.utc)
                
                try:
                    feed_data = feedparser.parse(feed.url, 
                        response_headers={'date': current_time.strftime("%a, %d %b %Y %H:%M:%S GMT")})
                    
                    if hasattr(feed_data, 'bozo_exception'):
                        logger.warning(f"Feed {feed.name} has format issues: {feed_data.bozo_exception}")
                    
                    for entry in feed_data.entries:
                        # Create a new session for each article
                        with self.app.app_context():
                            try:
                                title = html.unescape(entry.get('title', 'No title'))
                                url = entry.get('link', '')
                                
                                # Check if article exists
                                existing = Article.query.filter_by(url=url).first()
                                if existing:
                                    continue
                                    
                                author = entry.get('author', None)
                                
                                # Handle various date formats
                                published = None
                                for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                                    if date_field in entry and entry[date_field]:
                                        published = entry[date_field]
                                        break
                                if not published:
                                    published = time.localtime()
                                
                                # Get summary and content
                                summary = html.unescape(entry.get('summary', ''))
                                if not summary and 'description' in entry:
                                    summary = html.unescape(entry.description)
                                
                                content = ''
                                if 'content' in entry:
                                    content = html.unescape(entry.content[0].value)
                                elif hasattr(entry, 'content_encoded'):
                                    content = html.unescape(entry.content_encoded)
                                
                                published_dt = datetime(*published[:6], tzinfo=timezone.utc)
                                
                                article = Article(
                                    feed_id=feed.id,
                                    title=title,
                                    url=url,
                                    published=published_dt,
                                    summary=summary,
                                    content=content,
                                    author=author
                                )
                                
                                self.db.session.add(article)
                                self.db.session.commit()
                                
                            except Exception as entry_error:
                                self.db.session.rollback()
                                logger.error(f"Error processing entry: {str(entry_error)}")
                                continue
                    
                    logger.info(f"Successfully processed feed: {feed.name}")
                    
                except Exception as feed_error:
                    logger.error(f"Error processing feed: {str(feed_error)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Database error while processing feeds: {str(e)}")
            raise

def main():
    """Main entry point for the feed collector."""
    parser = argparse.ArgumentParser(description='RSS Feed Collector')
    
    parser.add_argument('--interval', type=int, default=3600,
                       help='Run interval in seconds (default: 3600 for 1 hour)')
    parser.add_argument('--cron', action='store_true',
                       help='Run once and exit (for cron jobs)')
    
    args = parser.parse_args()
    
    try:
        while True:
            collector = FeedCollector()
            collector.collect_articles()
            
            if args.cron:
                logger.info("Running in cron mode - exiting after single execution")
                break
                
            logger.info(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Feed collection stopped by user")
    except Exception as e:
        logger.error(f"Feed collection failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()