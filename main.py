import uvicorn

from app import app
from config import APP_HOST, APP_PORT

if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)