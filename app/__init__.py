from flask import Flask
from config import config
from .utils import from_json
from .blueprints import auth, api, web
import markdown2
import bleach

def create_app(config_name):
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    if hasattr(config[config_name], 'init_app'):
        config[config_name].init_app(app)
    
    def markdown_filter(text):
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
    
    # Register filters
    app.jinja_env.filters['from_json'] = from_json
    app.jinja_env.filters['markdown'] = markdown_filter
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(api)
    app.register_blueprint(web)
    
    return app