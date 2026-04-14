from flask import Flask
from config import Config
from routes.main_routes import main_bp
from routes.auth import auth_bp
from werkzeug.security import generate_password_hash
from models.db import get_db_connection

app = Flask(__name__)
app.config.from_object(Config)

# Dono routes ko link kar rahe hain
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

# Naya secure function jo Render par auto-admin banayega
def create_default_admin():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check karo ki Admin pehle se hai ya nahi
        cursor.execute("SELECT * FROM Users WHERE Username = 'Admin'")
        admin_exists = cursor.fetchone()
        
        if not admin_exists:
            # Sirf tabhi banayega jab naya database ho
            hashed_pw = generate_password_hash('Admin@9990')
            cursor.execute("""
                INSERT INTO Users (Username, PasswordHash, Role, Email, Level, XP) 
                VALUES ('Admin', ?, 'Admin', 'admin@gamingrp.com', 1, 0)
            """, (hashed_pw,))
            conn.commit()
            print("Secure Default Admin created successfully!")
            
        conn.close()
    except Exception as e:
        print(f"Admin creation skipped or error: {e}")

# Jab bhi tumhara server start hoga, ye automatically Admin ko check/create kar dega
create_default_admin()

if __name__ == '__main__':
    app.run(debug=True, port=5000)