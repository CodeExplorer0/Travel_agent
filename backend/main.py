from flask import Flask, request, jsonify
from flask_cors import CORS
from collaborative_workspace.socket_io import socketio
from backend.main import blueprint as api_blueprint

app = Flask(__name__)
CORS(app)

# Register API blueprint
app.register_blueprint(api_blueprint, url_prefix="/api")

# Initialize Socket.IO
socketio.init_app(app, cors_allowed_origins="*")

@app.route("/")
def home():
    return "Welcome to the Personalized Travel Itinerary Generator API!"

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
