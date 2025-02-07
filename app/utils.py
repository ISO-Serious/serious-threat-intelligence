import json
import logging

logger = logging.getLogger(__name__)

def from_json(data):
    """Handle JSON data that might still be in string form."""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return {}
    return data