#!/bin/bash

# Remove the old directory if it exists
rm -rf ready_to_copy

# Create a fresh destination directory
mkdir -p ready_to_copy

# Find and copy all Python files
find . -type f -name "*.py" -not -path "./ready_to_copy/*" -not -path "./venv/*" -not -path "./.venv/*" -not -path "*/__pycache__/*" -exec cp {} ready_to_copy/ \;

# Find and copy template files
find . -type f \( -name "*.html" -o -name "*.jinja" -o -name "*.jinja2" \) -not -path "./ready_to_copy/*" -not -path "./venv/*" -not -path "./.venv/*" -not -path "*/__pycache__/*" -exec cp {} ready_to_copy/ \;

# Find and copy static files
find . -type f \( \
    -name "*.css" -o \
    -name "*.js" \
    \) -not -path "./ready_to_copy/*" -not -path "./venv/*" -not -path "./.venv/*" -not -path "*/__pycache__/*" -exec cp {} ready_to_copy/ \;

# Copy configuration files
find . -type f \( \
    -name "requirements.txt" -o \
    -name ".env" -o \
    -name ".flaskenv" -o \
    -name "Procfile" -o \
    -name "wsgi.py" \
    \) -not -path "./ready_to_copy/*" -not -path "./venv/*" -not -path "./.venv/*" -not -path "*/__pycache__/*" -exec cp {} ready_to_copy/ \;

echo "Flask application files have been copied to ready_to_copy directory"