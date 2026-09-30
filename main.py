import uvicorn

from app import app
from comfyreview.settings import load_settings

if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        ssl_certfile=(
            str(settings.ssl_certificate_path)
            if settings.ssl_enabled
            else None
        ),
        ssl_keyfile=(
            str(settings.ssl_key_path) if settings.ssl_enabled else None
        ),
    )
