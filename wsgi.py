import os
from app import create_app

# Always use production config on Render
app = create_app('production')