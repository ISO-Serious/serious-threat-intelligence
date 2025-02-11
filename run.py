import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()

# Get config name from environment variable, default to 'production' for Render
config_name = os.environ.get('FLASK_ENV', 'production')
app = create_app(config_name)

if __name__ == '__main__':
    app.run()