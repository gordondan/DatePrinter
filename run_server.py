#!/usr/bin/env python
"""
Alternative server runner using gevent
This bypasses Flask's built-in host validation
"""
from gevent.pywsgi import WSGIServer
from server import app
import sys

PORT = 5000

print(f"Starting server on http://0.0.0.0:{PORT}")
print(f"Public URL: http://thunderbelly.duckdns.org/app/date-printer")
print("\nPress Ctrl+C to stop\n")

# Create a WSGI server with gevent
http_server = WSGIServer(('0.0.0.0', PORT), app)

try:
    http_server.serve_forever()
except KeyboardInterrupt:
    print("\nShutting down...")
    sys.exit(0)