"""
cPanel Passenger WSGI/ASGI entry point.

Passenger imports this file and looks for the callable named `application`.
For FastAPI (ASGI), Passenger handles the ASGI protocol automatically
when configured as a Python application in cPanel.
"""
import sys
import os

# Ensure the repo root is on the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app as application
