import os
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import app
sys.path.append(str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models import Feed, Article, DailySummary

def get_db():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    return app, db