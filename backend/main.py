from fastapi import FastAPI
import uvicorn
from collaborative_workspace.socket_io import create_socket_app

app = FastAPI()

# Create the Socket.IO app and integrate it with FastAPI
sio_app = create_socket_app(app)

@app.get("/")
async def index():
    return open("frontend/templates/index.html").read()

if __name__ == "__main__":
    uvicorn.run(sio_app, host="0.0.0.0", port=8000)
