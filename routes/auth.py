from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

# REGISTER
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT UserId FROM Users WHERE Username=? OR Email=?",
                (username, email)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                flash("Username ya Email already use ho raha hai!", "error")
                conn.close()
                return redirect(url_for('auth.register'))

            cursor.execute(
                "INSERT INTO Users (Username, Email, PasswordHash, Role) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, 'User')
            )

            new_user_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO Wallet (UserId, Coins) VALUES (?, ?)",
                (new_user_id, 0)
            )

            conn.commit()
            flash("Account create ho gaya! Login karo.", "success")
            conn.close()

            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"Error: {e}", "error")

    return render_template('register.html')


# LOGIN
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT UserId, Username, PasswordHash, Role, IsBanned FROM Users WHERE Username=?",
            (username,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["PasswordHash"], password):

            if user["IsBanned"] == 1:
                flash("Your account is banned!", "error")
                return redirect(url_for('auth.login'))

            session['user_id'] = user["UserId"]
            session['username'] = user["Username"]
            session['role'] = user["Role"]

            return redirect(url_for('main.dashboard'))

        else:
            flash("Galat username ya password!", "error")

    return render_template('login.html')


# LOGOUT
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))


# FORGOT PASSWORD
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        new_password = request.form['new_password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT UserId FROM Users WHERE Username=? AND Email=?",
            (username, email)
        )

        user = cursor.fetchone()

        if user:
            hashed_password = generate_password_hash(new_password)

            cursor.execute(
                "UPDATE Users SET PasswordHash=? WHERE UserId=?",
                (hashed_password, user["UserId"])
            )

            conn.commit()
            flash("Password reset successful!", "success")
            conn.close()

            return redirect(url_for('auth.login'))

        else:
            conn.close()
            flash("Invalid Username or Email!", "error")

    return render_template('forgot_password.html')