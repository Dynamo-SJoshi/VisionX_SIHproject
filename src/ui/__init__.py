# File: src/ui/__init__.py
"""
FastAPI backend and Streamlit frontend user interface package.
"""

try:
    from .backend import app, start_backend_server
    __all__ = ["app", "start_backend_server"]
except ImportError:
    __all__ = []
