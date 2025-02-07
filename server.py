from flask import Flask, jsonify, Response, render_template_string
import sqlite3
import logging
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def format_content(text):
    """
    Convert a formatted string with newlines and bullet points into HTML.
    
    Args:
        text (str): Input text with \n as newlines and • as bullet points
        
    Returns:
        str: HTML formatted string
    """
    # First, clean up the text
    text = text.rstrip('",').replace('\\n', '\n')
    
    # Split into sections
    sections = text.split('\n\n')
    html_parts = []
    
    for section in sections:
        if not section.strip():
            continue
            
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        if not lines:  # Skip empty sections
            continue
        
        # Handle section headers
        if lines[0].isupper() or '🔒' in lines[0]:
            # Remove emojis and clean the header
            header = lines[0].replace('🔒', '').strip()
            html_parts.append(f'<h2>{header}</h2>')
            lines = lines[1:]
            if not lines:  # Skip if no more lines after header
                continue
        
        # Start a new list if we have bullet points
        current_list = []
        in_sublist = False
        
        for line in lines:
            # Main bullet point
            if line.startswith('•'):
                # Close previous sublist if exists
                if current_list and in_sublist:
                    current_list.append('</ul></li>')
                    in_sublist = False
                
                if not current_list:
                    html_parts.append('<ul>')
                html_parts.append(f'<li>{line[1:].strip()}')
                current_list = []
                
            # Sub bullet point
            elif line.startswith('-'):
                if not in_sublist:
                    html_parts.append('<ul>')
                    in_sublist = True
                html_parts.append(f'<li>{line[1:].strip()}</li>')
                
            # Regular text
            else:
                if in_sublist:
                    html_parts.append('</ul></li>')
                    in_sublist = False
                if current_list:
                    html_parts.append('</ul>')
                    current_list = []
                html_parts.append(f'<p>{line}</p>')
        
        # Close any open lists
        if in_sublist:
            html_parts.append('</ul></li>')
        if current_list or in_sublist:
            html_parts.append('</ul>')
    
    return '\n'.join(html_parts)



# HTML template for the email view
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News Summary</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            text-transform: uppercase;
            font-size: 1.2em;
        }
        .category {
            margin-bottom: 40px;
            background: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
        }
        .date {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }
        .bullet {
            margin: 10px 0;
            padding-left: 20px;
            position: relative;
        }
        .sub-bullet {
            margin: 5px 0 5px 20px;
            color: #555;
        }
        strong {
            color: #2c3e50;
            display: block;
            margin-top: 15px;
            margin-bottom: 5px;
        }
        br {
            line-height: 150%;
        }
    </style>
</head>
<body>
    <h1>Daily News Summary</h1>
    <div class="date">{{ date }}</div>
    {% for category, content in summary.items() %}
    <div class="category">
        <h2>{{ category }}</h2>
        {{ format_content(content) | safe }}
    </div>
    {% endfor %}
</body>
</html>
"""

class SummaryServer:
    """Provides a web interface to access the generated summaries."""
    
    def __init__(self, db_path: str):
        """Initialize the Flask server with database path."""
        self.app = Flask(__name__)
        self.db_path = db_path
        
        if not Path(db_path).exists():
            raise FileNotFoundError(
                f"Database not found at {db_path}. Please run the setup script first."
            )
        
        # Add format_content function to template context
        self.app.jinja_env.globals.update(format_content=format_content)
        
        # Register routes
        self.app.route('/summary')(self.get_summary)
        self.app.route('/email')(self.get_email)
        self.app.route('/health')(self.health_check)
    
    def get_latest_summary(self):
        """Helper method to retrieve the latest summary from the database."""
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            
            # Get the most recent complete summary
            result = c.execute('''
                SELECT summary, date, generated_at 
                FROM daily_summaries 
                WHERE status = 'complete'
                ORDER BY generated_at DESC 
                LIMIT 1
            ''').fetchone()
            
            if result:
                return {
                    'summary': json.loads(result[0]),
                    'date': result[1],
                    'generated_at': result[2]
                }
            return None
                
        finally:
            conn.close()
    
    def get_summary(self):
        """Endpoint to retrieve the most recent daily summary as JSON."""
        try:
            result = self.get_latest_summary()
            
            if result:
                return jsonify(result['summary'])
            else:
                return jsonify({
                    "error": "No summary available",
                    "message": "No recent summaries found in the database"
                }), 404
                
        except Exception as e:
            logger.error(f"Error retrieving summary: {str(e)}")
            return jsonify({
                "error": "Failed to retrieve summary",
                "message": str(e)
            }), 500
    
    def get_email(self):
        """Endpoint to retrieve the most recent daily summary as formatted HTML."""
        try:
            result = self.get_latest_summary()
            
            if result:
                # Format the date nicely
                date_str = datetime.fromisoformat(result['date']).strftime('%A, %B %d, %Y')
                
                # Render the HTML template with the summary data
                return render_template_string(
                    EMAIL_TEMPLATE,
                    summary=result['summary'],
                    date=date_str
                )
            else:
                return "No recent summaries found in the database", 404
                
        except Exception as e:
            logger.error(f"Error generating email view: {str(e)}")
            return f"Error generating email view: {str(e)}", 500
    
    def health_check(self):
        """Simple health check endpoint for monitoring."""
        return Response("OK", status=200)
    
    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """Run the Flask server."""
        self.app.run(host=host, port=port)

def main():
    """Main entry point for the summary server."""
    parser = argparse.ArgumentParser(description='RSS Feed Summary Server')
    
    parser.add_argument('--db', default='rss_feeds.db',
                       help='Database file path (default: rss_feeds.db)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port for the summary server (default: 5000)')
    
    args = parser.parse_args()
    
    try:
        # Initialize and start the web server
        server = SummaryServer(args.db)
        server.run(port=args.port)
        
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()