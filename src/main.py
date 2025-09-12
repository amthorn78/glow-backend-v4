#!/usr/bin/env python3
"""
GLOW Backend - Main Entry Point
Production deployment entry point for the GLOW dating app backend
"""

import sys
import os

from app import app

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=False)

