import uvicorn

from app import app
from config import APP_HOST, APP_PORT, SSL_ENABLED, SSL_CERTFILE, SSL_KEYFILE

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=APP_HOST,
        port=APP_PORT,
        ssl_certfile=str(SSL_CERTFILE) if SSL_ENABLED else None,
        ssl_keyfile=str(SSL_KEYFILE) if SSL_ENABLED else None,
    )