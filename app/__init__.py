from flask import Flask
from config import config
from app.utils import from_json
import markdown2
import bleach

def create_app(config_name):
    app = Flask(__name__)
    
    # Load the config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app) if hasattr(config[config_name], 'init_app') else None
    
    def markdown_filter(text):
        # Convert markdown to HTML
        html = markdown2.markdown(
            text,
            extras=[
                'fenced-code-blocks',
                'tables',
                'break-on-newline',
                'target-blank-links'
            ]
        )
        
        # Sanitize HTML
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
        
        clean_html = bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True
        )
        
        return clean_html
    
    # Register template filters
    app.jinja_env.filters['from_json'] = from_json
    app.jinja_env.filters['markdown'] = markdown_filter
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app