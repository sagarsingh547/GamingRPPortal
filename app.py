from flask import Flask
from config import Config
from routes.main_routes import main_bp
from routes.auth import auth_bp

app = Flask(__name__)
app.config.from_object(Config)

# Dono routes ko link kar rahe hain
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)