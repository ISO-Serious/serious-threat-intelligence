from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config
import markdown2
import bleach
from .extensions import db, migrate
from .blueprints import auth, api, web

def create_app(config_name):
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    if hasattr(config[config_name], 'init_app'):
        config[config_name].init_app(app)
    
    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models
    from .models import Feed, Article, DailySummary
    
    def markdown_filter(text):
        if text is None:
            return ""
            
        html = markdown2.markdown(
            text,
            extras=['fenced-code-blocks', 'tables', 'break-on-newline', 'target-blank-links']
        )
        
        allowed_tags = [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr',
            'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre',
            'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
        ]
        allowed_attrs = {
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title'],
            '*': ['class']
        }
        
        return bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True
        )
    
    def from_json(value):
        try:
            return json.loads(value)
        except:
            return value
    
    # Register filters
    app.jinja_env.filters['markdown'] = markdown_filter
    app.jinja_env.filters['from_json'] = from_json
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(api)
    app.register_blueprint(web)

    # Register CLI commands
    from app.commands import create_admin_command
    app.cli.add_command(create_admin_command)
    
    return app

# Import utils after create_app to avoid circular imports
from .utils import from_json