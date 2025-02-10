import json
import logging

logger = logging.getLogger(__name__)

def normalize_json_string(s):
    replacements = [
        ('\\\\n', '\n'),
        ('\\\\"', '"'),
        ('\\\\\'', "'"),
        ('\\n', '\n'),
        ('\\"', '"'),
        ('\\\'', "'"),
        ('\\\\', '\\')
    ]
    
    for old, new in replacements:
        s = s.replace(old, new)
    
    return s

def parse_double_encoded_json(s):
    try:
        outer = json.loads(s)
        result = {}
        for key, value in outer.items():
            try:
                if isinstance(value, str):
                    normalized = normalize_json_string(value)
                    parsed = json.loads(normalized)
                    if isinstance(parsed, dict):
                        if 'summary' in parsed:
                            parsed['summary'] = normalize_json_string(parsed['summary'])
                        if 'actionable_tasks' in parsed:
                            for task in parsed['actionable_tasks']:
                                if 'description' in task:
                                    task['description'] = normalize_json_string(task['description'])
                    result[key] = parsed
                else:
                    result[key] = value
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing inner JSON for {key}: {str(e)}")
                logger.error(f"Value: {value[:200]}")
                result[key] = value
                
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing outer JSON: {str(e)}")
        return {}
    
def from_json(data):
    """Handle JSON data that might still be in string form."""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return {}
    return data