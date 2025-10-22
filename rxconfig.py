import reflex as rx

config = rx.Config(
    app_name="backbone",
    db_url="sqlite:///reflex.db",
    frontend_port=3000,
    backend_port=8000,
)
