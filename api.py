
# ASGI application entry point for deployment platforms like Render.


from app.api import create_app

app = create_app()
