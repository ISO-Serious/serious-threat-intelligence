import os
from pathlib import Path

class Config:
    # Base directory of the application
    BASE_DIR = Path(__file__).resolve().parent
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Database configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or str(BASE_DIR / 'rss_feeds.db')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # App settings
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 10))

    # Authentication settings
    AUTH_USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
    AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD', 'munk1luvver')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DEVELOPMENT = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # In production, SECRET_KEY should be set in environment
    @classmethod
    def init_app(cls, app):
        assert os.environ.get('SECRET_KEY'), 'SECRET_KEY environment variable must be set'
        
        # Set up production-specific logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            'logs/security_dashboard.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # Use SQLite in-memory database for testing
    DATABASE_PATH = ':memory:'


# Dictionary to map environment names to config classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}