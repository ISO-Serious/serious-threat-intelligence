import feedparser
from datetime import datetime, timezone, timedelta
import time
import html
import logging
import os
from pathlib import Path
import argparse
from db_helper import get_db, Feed, Article
from dateutil import parser as date_parser
from dateutil import tz

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and above by default
    format='%(message)s',  # Simplified format
    handlers=[
        logging.FileHandler('feed_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define timezone information for common US timezones
TIMEZONE_INFO = {
    'EST': tz.gettz('America/New_York'),
    'EDT': tz.gettz('America/New_York'),
    'CST': tz.gettz('America/Chicago'),
    'CDT': tz.gettz('America/Chicago'),
    'MST': tz.gettz('America/Denver'),
    'MDT': tz.gettz('America/Denver'),
    'PST': tz.gettz('America/Los_Angeles'),
    'PDT': tz.gettz('America/Los_Angeles'),
}

class FeedCollector:
    """Handles fetching and storing RSS feeds in the database."""
    
    def __init__(self):
        """Initialize the feed collector."""
        self.app, self.db = get_db()
        self.app.app_context().push()
        self.total_added = 0
        self.total_skipped = 0

    def _parse_date(self, entry):
        """Extract and parse the publication date from a feed entry."""
        current_time = datetime.now(timezone.utc)
        
        # Try getting the raw date strings first
        for date_field in ['published', 'updated', 'created']:
            if date_field in entry:
                try:
                    # Use dateutil parser with timezone information
                    parsed_time = date_parser.parse(entry[date_field], tzinfos=TIMEZONE_INFO)
                    if parsed_time:
                        # Convert to UTC if it's timezone-aware
                        if parsed_time.tzinfo:
                            parsed_time = parsed_time.astimezone(timezone.utc)
                        else:
                            parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                        
                        # Skip future dates
                        if parsed_time > current_time:
                            return current_time
                            
                        return parsed_time
                except Exception:
                    continue
        
        # Fallback to parsed tuples
        for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
            if date_field in entry and entry[date_field]:
                try:
                    parsed_time = datetime(*entry[date_field][:6], tzinfo=timezone.utc)
                    
                    # Skip future dates
                    if parsed_time > current_time:
                        return current_time
                        
                    return parsed_time
                except Exception:
                    continue
        
        # If all else fails, use current time
        return current_time

    def _is_recent_article(self, published_dt, current_time):
        """Check if the article was published within the last 2 hours."""
        time_threshold = current_time - timedelta(hours=2)
        return published_dt >= time_threshold

    def collect_articles(self):
        """Fetch articles from all active feeds and store them in the database."""
        try:
            # Get all active feeds from the database
            feeds = Feed.query.filter_by(active=True).all()
            
            for feed in feeds:
                current_time = datetime.now(timezone.utc)
                
                try:
                    # Add If-Modified-Since header to only get new content
                    time_threshold = current_time - timedelta(hours=2)
                    headers = {'date': current_time.strftime("%a, %d %b %Y %H:%M:%S GMT")}
                    
                    feed_data = feedparser.parse(feed.url, response_headers=headers)
                    
                    if hasattr(feed_data, 'status'):
                        if feed_data.status >= 400:
                            logger.warning(f"Error fetching {feed.name}: HTTP {feed_data.status}")
                            continue
                    
                    for entry in feed_data.entries:
                        try:
                            title = html.unescape(entry.get('title', 'No title'))
                            url = entry.get('link', '')
                            
                            # Skip if article already exists
                            if Article.query.filter_by(url=url).first():
                                self.total_skipped += 1
                                continue
                                
                            author = entry.get('author', None)
                            published_dt = self._parse_date(entry)
                            
                            # Skip if article is not recent enough
                            if not self._is_recent_article(published_dt, current_time):
                                self.total_skipped += 1
                                continue
                            
                            # Get summary and content
                            summary = html.unescape(entry.get('summary', ''))
                            if not summary and 'description' in entry:
                                summary = html.unescape(entry.description)
                            
                            content = ''
                            if 'content' in entry:
                                content = html.unescape(entry.content[0].value)
                            elif hasattr(entry, 'content_encoded'):
                                content = html.unescape(entry.content_encoded)
                            
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
                            self.total_added += 1
                            
                        except Exception as entry_error:
                            self.db.session.rollback()
                            continue
                    
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Database error while processing feeds: {str(e)}")
            raise

        # Log the final totals
        logger.warning(f"Articles added: {self.total_added}, skipped: {self.total_skipped}")

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
                logger.warning("Running in cron mode - exiting after single execution")
                break
                
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Feed collection failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()