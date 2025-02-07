import sqlite3
import json
import argparse
import sys
import logging
from typing import List, Dict
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self, db_path: str = 'rss_feeds.db'):
        """Initialize database setup with the specified database path."""
        self.db_path = db_path

    def initialize_database(self):
        """Create the database schema if it doesn't exist."""
        logger.info(f"Initializing database at {self.db_path}")
        
        # Create database directory if it doesn't exist
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create feeds table
        c.execute('''CREATE TABLE IF NOT EXISTS feeds
                     (id INTEGER PRIMARY KEY,
                      url TEXT UNIQUE,
                      name TEXT,
                      category TEXT,
                      active BOOLEAN DEFAULT 1)''')
        
        # Create articles table with more metadata
        c.execute('''CREATE TABLE IF NOT EXISTS articles
                     (id INTEGER PRIMARY KEY,
                      feed_id INTEGER,
                      title TEXT,
                      url TEXT UNIQUE,
                      published TIMESTAMP,
                      summary TEXT,
                      content TEXT,
                      author TEXT,
                      FOREIGN KEY (feed_id) REFERENCES feeds(id))''')
        
        # Create daily summaries table
        c.execute('''CREATE TABLE IF NOT EXISTS daily_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        summary JSON NOT NULL,  -- Use JSON type
                        generated_at TEXT NOT NULL,
                        status TEXT NOT NULL
                    )''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialization completed successfully")

    def import_feeds(self, config_file: str):
        """Import feeds from a JSON configuration file."""
        logger.info(f"Importing feeds from {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                feed_config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_file} not found")
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file {config_file}")
            sys.exit(1)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for feed in feed_config['feeds']:
            try:
                c.execute('''INSERT OR REPLACE INTO feeds (url, name, category)
                            VALUES (?, ?, ?)''',
                         (feed['url'], feed['name'], feed.get('category', 'General')))
                logger.info(f"Added/updated feed: {feed['name']}")
            except sqlite3.Error as e:
                logger.error(f"Error importing feed {feed['name']}: {str(e)}")

        conn.commit()
        conn.close()
        logger.info("Feed import completed successfully")

    def list_feeds(self):
        """List all configured feeds in the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        feeds = c.execute('''SELECT name, url, category, active 
                            FROM feeds 
                            ORDER BY category, name''').fetchall()
        
        if not feeds:
            logger.info("No feeds configured in the database")
            return

        print("\nConfigured Feeds:")
        print("-" * 80)
        current_category = None
        
        for name, url, category, active in feeds:
            if category != current_category:
                print(f"\n{category}:")
                current_category = category
            
            status = "Active" if active else "Inactive"
            print(f"  - {name}")
            print(f"    URL: {url}")
            print(f"    Status: {status}")
        
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='RSS Feed Aggregator Setup')
    parser.add_argument('--db', default='../rss_feeds.db',
                       help='Database file path (default: rss_feeds.db)')
    parser.add_argument('--config', help='Feed configuration JSON file', default='feeds.json')
    parser.add_argument('--list', action='store_true',
                       help='List configured feeds')
    
    args = parser.parse_args()
    
    db_path = os.getenv('DATABASE_PATH') or args.db
    setup = DatabaseSetup(db_path)
    
    # Initialize database
    setup.initialize_database()
    
    # Import feeds if config file provided
    if args.config:
        setup.import_feeds(args.config)
    
    # List feeds if requested
    if args.list:
        setup.list_feeds()

if __name__ == '__main__':
    main()