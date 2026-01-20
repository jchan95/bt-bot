"""
Vercel Serverless Function Entry Point
This file exposes the FastAPI app for Vercel deployment.
"""

from app.main import app

# Vercel requires the handler to be named 'app' or 'handler'
# FastAPI's ASGI app works directly with Vercel
handler = app
