import feedparser
from datetime import datetime, timezone
import sqlite3
import time
import html
import logging
from pathlib import Path
import argparse

# Configure feedparser to use the newer date handler
feedparser.datetimes.registerDateHandler(lambda date_string: datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ"))

# Configure SQLite to properly handle datetime objects
def adapt_datetime(dt):
    """Convert datetime objects to SQLite TEXT format."""
    return dt.isoformat()

def convert_datetime(text):
    """Convert SQLite TEXT format back to datetime objects."""
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    try:
        date_obj = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f")
        return date_obj.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            date_obj = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S")
            return date_obj.replace(tzinfo=timezone.utc)
        except ValueError:
            return text

# Register the datetime adapters with SQLite
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

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
    
    def __init__(self, db_path: str):
        """Initialize the feed collector with database path."""
        self.db_path = db_path
        
        if not Path(db_path).exists():
            raise FileNotFoundError(
                f"Database not found at {db_path}. Please run the setup script first."
            )
    
    def collect_articles(self):
        """Fetch articles from all active feeds and store them in the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get all active feeds from the database
            feeds = c.execute('''
                SELECT id, url, name, category 
                FROM feeds 
                WHERE active = 1
            ''').fetchall()
            
            for feed_id, feed_url, feed_name, category in feeds:
                try:
                    logger.info(f"Fetching articles from {feed_name}")
                    current_time = datetime.now(timezone.utc)
                    feed = feedparser.parse(feed_url, response_headers={'date': current_time.strftime("%a, %d %b %Y %H:%M:%S GMT")})
                    
                    if hasattr(feed, 'bozo_exception'):
                        logger.warning(f"Feed {feed_name} has format issues: {feed.bozo_exception}")
                    
                    for entry in feed.entries:
                        try:
                            # Extract and clean article data
                            title = html.unescape(entry.get('title', 'No title'))
                            url = entry.get('link', '')
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
                            
                            c.execute('''
                                INSERT OR IGNORE INTO articles 
                                (feed_id, title, url, published, summary, content, author)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (feed_id, title, url, published_dt, summary, content, author))
                            
                        except Exception as entry_error:
                            logger.error(f"Error processing entry in feed {feed_name}: {str(entry_error)}")
                            continue
                    
                    logger.info(f"Successfully processed feed: {feed_name}")
                
                except Exception as feed_error:
                    logger.error(f"Error processing feed {feed_url}: {str(feed_error)}")
                    continue
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Database error while processing feeds: {str(e)}")
            raise
        
        finally:
            conn.close()

def main():
    """Main entry point for the feed collector."""
    parser = argparse.ArgumentParser(description='RSS Feed Collector')
    
    parser.add_argument('--db', default='../rss_feeds.db',
                       help='Database file path (default: rss_feeds.db)')
    parser.add_argument('--interval', type=int, default=3600,
                       help='Run interval in seconds (default: 3600 for 1 hour)')
    
    args = parser.parse_args()
    
    try:
        while True:
            collector = FeedCollector(args.db)
            collector.collect_articles()
            logger.info(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Feed collection stopped by user")
    except Exception as e:
        logger.error(f"Feed collection failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()