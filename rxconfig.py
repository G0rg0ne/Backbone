import reflex as rx
import os

config = rx.Config(
    app_name="backbone",
    db_url="sqlite:///reflex.db",
    frontend_port=3000,
    backend_port=8001,  # Use different port to avoid conflict with document processor
    backend_host="0.0.0.0",  # Explicitly set backend host for Docker
)
