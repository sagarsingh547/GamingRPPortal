import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models.db import get_db_connection
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# MAINTENANCE MODE
@main_bp.before_app_request
def check_maintenance():
    allowed = ['static', 'auth.login', 'auth.logout', 'main.maintenance_page']

    if request.endpoint in allowed:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT SettingValue FROM SystemSettings WHERE SettingKey=?",
            ('MaintenanceMode',)
        )
        row = cursor.fetchone()
    except:
        row = None
    finally:
        conn.close()

    if row and row["SettingValue"] == '1':
        if session.get('role') != 'Admin':
            return render_template('maintenance.html')


@main_bp.route('/maintenance')
def maintenance_page():
    return render_template('maintenance.html')


# HOME PAGE
@main_bp.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT Title, Content, PostedDate FROM Announcements ORDER BY PostedDate DESC"
        )
        announcements = cursor.fetchall()
    except:
        announcements = []
    finally:
        conn.close()

    return render_template('index.html', announcements=announcements)


# --- DASHBOARD ---
@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # FIX 1: LEFT JOIN use kiya hai taki Wallet na hone par bhi crash na ho
        cursor.execute("""
            SELECT u.Username, u.Role, u.Level, u.XP, w.Coins
            FROM Users u
            LEFT JOIN Wallet w ON u.UserId = w.UserId
            WHERE u.UserId = ?
        """, (user_id,))
        user_data = cursor.fetchone()

        # Agar data puri tarah corrupt hai to session clear kar do
        if not user_data:
            session.clear()
            flash("Account data error! Please login again.", "error")
            return redirect(url_for('auth.login'))

        # LAST 5 TRANSACTIONS
        cursor.execute("""
            SELECT Amount, Type, Description, TransactionDate
            FROM Transactions
            WHERE UserId = ?
            ORDER BY TransactionDate DESC
            LIMIT 5
        """, (user_id,))
        transactions = cursor.fetchall()
        
    except Exception as e:
        print(f"DASHBOARD ERROR: {e}")
        flash("Dashboard load hone me error aayi.", "error")
        user_data = None 
        transactions = []
    finally:
        conn.close()

    return render_template(
        'dashboard.html',
        user=user_data,
        transactions=transactions
    )


# DAILY REWARD
@main_bp.route('/daily_bonus', methods=['POST'])
def daily_bonus():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT LastDailyReward, Coins FROM Wallet WHERE UserId=?", (user_id,))
        row = cursor.fetchone()

        now = datetime.now()
        can_claim = True

        # Date checking logic (Safe Parsing)
        if row and row["LastDailyReward"]:
            try:
                old_time_str = str(row["LastDailyReward"]).split('.')[0] 
                old_time = datetime.strptime(old_time_str, '%Y-%m-%d %H:%M:%S')
                if now - old_time < timedelta(days=1):
                    can_claim = False
            except Exception as e:
                print(f"Date check skipped due to format issue: {e}")

        if not can_claim:
            flash("Aaj ka reward already le liya! 24 hours wait karo.", "error")
            return redirect(url_for('main.dashboard'))

        # Safely get current XP and Level
        cursor.execute("SELECT XP, Level FROM Users WHERE UserId=?", (user_id,))
        xp_row = cursor.fetchone()

        current_xp = int(xp_row["XP"]) if (xp_row and xp_row["XP"] is not None) else 0
        current_level = int(xp_row["Level"]) if (xp_row and xp_row["Level"] is not None) else 1

        new_xp = current_xp + 50
        new_level = int(new_xp // 100) + 1

        # Update Wallet Safely 
        current_coins = int(row["Coins"]) if (row and row["Coins"] is not None) else 0
        new_coins = current_coins + 500
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("""
            UPDATE Wallet
            SET Coins = ?, LastDailyReward = ?
            WHERE UserId = ?
        """, (new_coins, now_str, user_id))

        # Agar pehle se wallet table me entry nahi thi, to bana do
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO Wallet (UserId, Coins, LastDailyReward)
                VALUES (?, ?, ?)
            """, (user_id, new_coins, now_str))

        # Update XP and Level
        cursor.execute("""
            UPDATE Users
            SET XP = ?, Level = ?
            WHERE UserId = ?
        """, (new_xp, new_level, user_id))

        # Add Transaction
        cursor.execute("""
            INSERT INTO Transactions (UserId, Amount, Type, Description, TransactionDate)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, 500, 'Credit', 'Daily Reward Claimed', now_str))

        conn.commit()
        flash(f"500 Coins + 50 XP mil gaya! (Level {new_level})", "success")

    except Exception as e:
        print(f"DAILY BONUS ERROR: {e}")
        conn.rollback() 
        flash("Reward claim karte time error aayi.", "error")
    finally:
        conn.close()

    return redirect(url_for('main.dashboard'))


# SHOP
@main_bp.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT ItemId, ItemName, Description, Price, ItemType
            FROM ShopItems
        """)
        items = cursor.fetchall()

        cursor.execute(
            "SELECT Coins FROM Wallet WHERE UserId=?",
            (session['user_id'],)
        )
        wallet = cursor.fetchone()
    except:
        items = []
        wallet = None
    finally:
        conn.close()

    return render_template(
        'shop.html',
        items=items,
        user_coins=wallet["Coins"] if wallet else 0
    )


# BUY ITEM
@main_bp.route('/buy/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT ItemName, Price FROM ShopItems WHERE ItemId=?",
            (item_id,)
        )
        item = cursor.fetchone()

        if item:
            cursor.execute(
                "SELECT Coins FROM Wallet WHERE UserId=?",
                (user_id,)
            )
            wallet = cursor.fetchone()

            if wallet and wallet["Coins"] >= item["Price"]:
                cursor.execute("""
                    UPDATE Wallet
                    SET Coins = Coins - ?
                    WHERE UserId = ?
                """, (item["Price"], user_id))

                cursor.execute("""
                    INSERT INTO Inventory (UserId, ItemId, AcquiredDate)
                    VALUES (?, ?, ?)
                """, (user_id, item_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

                cursor.execute("""
                    INSERT INTO Transactions
                    (UserId, Amount, Type, Description, TransactionDate)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    item["Price"],
                    'Debit',
                    f'Purchased {item["ItemName"]}',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))

                conn.commit()
                flash("Purchase successful!", "success")
            else:
                flash("Coins kam hain!", "error")
    except Exception as e:
        print(f"BUY ITEM ERROR: {e}")
        conn.rollback()
        flash("Kuch error aa gaya purchase me.", "error")
    finally:
        conn.close()

    return redirect(url_for('main.shop'))


# INVENTORY
@main_bp.route('/inventory')
def inventory():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT s.ItemName, s.Description, s.ItemType, i.AcquiredDate
            FROM Inventory i
            JOIN ShopItems s ON i.ItemId = s.ItemId
            WHERE i.UserId=?
            ORDER BY i.AcquiredDate DESC
        """, (session['user_id'],))
        my_items = cursor.fetchall()
    except:
        my_items = []
    finally:
        conn.close()

    return render_template('inventory.html', items=my_items)


# LEADERBOARD
@main_bp.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT u.Username, u.Level, u.XP, w.Coins
            FROM Users u
            LEFT JOIN Wallet w ON u.UserId = w.UserId
            ORDER BY u.Level DESC, u.XP DESC
            LIMIT 10
        """)
        top_users = cursor.fetchall()
    except:
        top_users = []
    finally:
        conn.close()

    return render_template('leaderboard.html', users=top_users)


# TICKETS
@main_bp.route('/tickets', methods=['GET', 'POST'])
def tickets():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if request.method == 'POST':
            cursor.execute("""
                INSERT INTO Tickets (UserId, Subject, Message, CreatedAt)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                request.form['subject'],
                request.form['message'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            flash("Ticket submit ho gaya!", "success")

        cursor.execute("""
            SELECT Subject, Message, Status, CreatedAt
            FROM Tickets
            WHERE UserId=?
            ORDER BY CreatedAt DESC
        """, (user_id,))
        my_tickets = cursor.fetchall()
    except Exception as e:
        print(f"TICKET ERROR: {e}")
        my_tickets = []
    finally:
        conn.close()

    return render_template('tickets.html', tickets=my_tickets)


# NOTIFICATIONS
@main_bp.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT Message, IsRead, CreatedAt
            FROM Notifications
            WHERE UserId=?
            ORDER BY CreatedAt DESC
        """, (session['user_id'],))
        data = cursor.fetchall()

        cursor.execute("""
            UPDATE Notifications
            SET IsRead=1
            WHERE UserId=? AND IsRead=0
        """, (session['user_id'],))
        conn.commit()
    except:
        data = []
    finally:
        conn.close()

    return render_template('notifications.html', notifications=data)


# PROFILE
@main_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if request.method == 'POST':
            # avatar upload
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    file.save(os.path.join(UPLOAD_FOLDER, filename))

                    cursor.execute("""
                        UPDATE Users
                        SET Avatar=?
                        WHERE UserId=?
                    """, (filename, user_id))
                    conn.commit()

            # password change
            if request.form.get('old_password') and request.form.get('new_password'):
                cursor.execute("SELECT PasswordHash FROM Users WHERE UserId=?", (user_id,))
                user = cursor.fetchone()

                if user and check_password_hash(user["PasswordHash"], request.form['old_password']):
                    new_hash = generate_password_hash(request.form['new_password'])
                    cursor.execute("""
                        UPDATE Users
                        SET PasswordHash=?
                        WHERE UserId=?
                    """, (new_hash, user_id))
                    conn.commit()
                    flash("Password changed!", "success")
                else:
                    flash("Old password galat hai!", "error")
            
            return redirect(url_for('main.profile'))

        cursor.execute("""
            SELECT Username, Email, Role, Level, XP, Avatar, CreatedAt
            FROM Users
            WHERE UserId=?
        """, (user_id,))
        user_info = cursor.fetchone()

    except Exception as e:
        print(f"PROFILE ERROR: {e}")
        user_info = None
    finally:
        conn.close()

    return render_template('profile.html', user=user_info)


# ADMIN PANEL
@main_bp.route('/admin')
def admin_panel():
    if session.get('role') != 'Admin':
        return redirect(url_for('main.dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT UserId, Username, Email, Role,
                   IsBanned, CreatedAt, WarningCount
            FROM Users
        """)
        users = cursor.fetchall()

        cursor.execute("""
            SELECT TicketId, Subject, Message, Status, CreatedAt
            FROM Tickets
            ORDER BY CreatedAt DESC
        """)
        tickets = cursor.fetchall()

        cursor.execute("""
            SELECT AnnouncementId, Title, PostedDate
            FROM Announcements
            ORDER BY PostedDate DESC
        """)
        announcements = cursor.fetchall()

        cursor.execute("""
            SELECT SettingValue
            FROM SystemSettings
            WHERE SettingKey=?
        """, ('MaintenanceMode',))
        row = cursor.fetchone()
        m_status = row["SettingValue"] == '1' if row else False

    except Exception as e:
        print(f"ADMIN ERROR: {e}")
        users, tickets, announcements, m_status = [], [], [], False
    finally:
        conn.close()

    return render_template(
        'admin.html',
        users=users,
        tickets=tickets,
        announcements=announcements,
        m_status=m_status
    )


# POST ANNOUNCEMENT
@main_bp.route('/post_announcement', methods=['POST'])
def post_announcement():
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Announcements (Title, Content, AuthorId, PostedDate)
            VALUES (?, ?, ?, ?)
        """, (
            request.form['title'],
            request.form['content'],
            session['user_id'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
    except Exception as e:
        print(f"ANNOUNCEMENT POST ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))


# DELETE ANNOUNCEMENT
@main_bp.route('/delete_announcement/<int:ann_id>')
def delete_announcement(ann_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Announcements WHERE AnnouncementId=?", (ann_id,))
        conn.commit()
    except Exception as e:
        print(f"ANNOUNCEMENT DELETE ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))


# TOGGLE MAINTENANCE
@main_bp.route('/toggle_maintenance')
def toggle_maintenance():
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT SettingValue FROM SystemSettings WHERE SettingKey=?", ('MaintenanceMode',))
        row = cursor.fetchone()

        new_val = '0' if (row and row["SettingValue"] == '1') else '1'

        cursor.execute("UPDATE SystemSettings SET SettingValue=? WHERE SettingKey=?", (new_val, 'MaintenanceMode'))
        conn.commit()
        flash("Maintenance mode updated!", "success")
    except Exception as e:
        print(f"MAINTENANCE TOGGLE ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))


# BAN USER
@main_bp.route('/ban_user/<int:user_id>')
def ban_user(user_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT IsBanned FROM Users WHERE UserId=?", (user_id,))
        row = cursor.fetchone()

        if row:
            new_status = 0 if row["IsBanned"] == 1 else 1
            cursor.execute("UPDATE Users SET IsBanned=? WHERE UserId=?", (new_status, user_id))
            conn.commit()
    except Exception as e:
        print(f"BAN USER ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))


# WARN USER
@main_bp.route('/warn_user/<int:user_id>')
def warn_user(user_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT WarningCount FROM Users WHERE UserId=?", (user_id,))
        row = cursor.fetchone()

        if row:
            warnings = row["WarningCount"] + 1
            banned = 1 if warnings >= 3 else 0
            
            cursor.execute("""
                UPDATE Users
                SET WarningCount=?, IsBanned=?
                WHERE UserId=?
            """, (min(warnings, 3), banned, user_id))
            conn.commit()
    except Exception as e:
        print(f"WARN USER ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))


# DELETE USER
@main_bp.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Users WHERE UserId=?", (user_id,))
        cursor.execute("DELETE FROM Wallet WHERE UserId=?", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"DELETE USER ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))


# CLOSE TICKET
@main_bp.route('/close_ticket/<int:ticket_id>')
def close_ticket(ticket_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE Tickets SET Status='Closed' WHERE TicketId=?", (ticket_id,))
        conn.commit()
    except Exception as e:
        print(f"CLOSE TICKET ERROR: {e}")
    finally:
        conn.close()

    return redirect(url_for('main.admin_panel'))