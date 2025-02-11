"""Add initial feeds data

Revision ID: a87b4c37fc6d
Revises: 6aa9e35b0cd4
Create Date: 2025-02-11 12:19:47.723403

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import json
from pathlib import Path

# revision identifiers, used by Alembic.
revision = 'a87b4c37fc6d'
down_revision = '6aa9e35b0cd4'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    try:
        # Read feeds from JSON
        json_path = Path(__file__).parent.parent.parent / 'cron' / 'feeds.json'
        with open(json_path, 'r') as f:
            feed_config = json.load(f)

        # Insert feeds
        for feed in feed_config['feeds']:
            connection.execute(
                text(
                    'INSERT INTO feeds (url, name, category, active) '
                    'VALUES (:url, :name, :category, :active) '
                    'ON CONFLICT (url) DO NOTHING'
                ),
                {
                    'url': feed['url'],
                    'name': feed['name'],
                    'category': feed.get('category', 'General'),
                    'active': True
                }
            )

        connection.commit()

    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise e

def downgrade():
    connection = op.get_bind()
    
    try:
        json_path = Path(__file__).parent.parent.parent / 'cron' / 'feeds.json'
        with open(json_path, 'r') as f:
            feed_config = json.load(f)
            
        urls = [feed['url'] for feed in feed_config['feeds']]
        connection.execute(
            text('DELETE FROM feeds WHERE url = ANY(:urls)'),
            {'urls': urls}
        )
        
        connection.commit()
        
    except Exception as e:
        print(f"Error during downgrade: {str(e)}")
        raise e