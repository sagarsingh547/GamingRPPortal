import sqlite3

conn = sqlite3.connect("gamingportal.db")
cursor = conn.cursor()

# USERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS Users (
    UserId INTEGER PRIMARY KEY AUTOINCREMENT,
    Username TEXT UNIQUE,
    Email TEXT UNIQUE,
    PasswordHash TEXT,
    Role TEXT DEFAULT 'User',
    Avatar TEXT DEFAULT 'default.png',
    Level INTEGER DEFAULT 1,
    XP INTEGER DEFAULT 0,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    IsBanned INTEGER DEFAULT 0,
    WarningCount INTEGER DEFAULT 0
)
""")

# WALLET
cursor.execute("""
CREATE TABLE IF NOT EXISTS Wallet (
    WalletId INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,
    Coins INTEGER DEFAULT 0,
    LastDailyReward TIMESTAMP
)
""")

# TRANSACTIONS
cursor.execute("""
CREATE TABLE IF NOT EXISTS Transactions (
    TransactionId INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,
    Amount INTEGER,
    Type TEXT,
    Description TEXT,
    TransactionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# SHOP ITEMS
cursor.execute("""
CREATE TABLE IF NOT EXISTS ShopItems (
    ItemId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemName TEXT,
    Description TEXT,
    Price INTEGER,
    ItemType TEXT
)
""")

# INVENTORY
cursor.execute("""
CREATE TABLE IF NOT EXISTS Inventory (
    InventoryId INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,
    ItemId INTEGER,
    AcquiredDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# NOTIFICATIONS
cursor.execute("""
CREATE TABLE IF NOT EXISTS Notifications (
    NotificationId INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,
    Message TEXT,
    IsRead INTEGER DEFAULT 0,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# TICKETS
cursor.execute("""
CREATE TABLE IF NOT EXISTS Tickets (
    TicketId INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,
    Subject TEXT,
    Message TEXT,
    Status TEXT DEFAULT 'Open',
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ANNOUNCEMENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS Announcements (
    AnnouncementId INTEGER PRIMARY KEY AUTOINCREMENT,
    Title TEXT,
    Content TEXT,
    AuthorId INTEGER,
    PostedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# SETTINGS
cursor.execute("""
CREATE TABLE IF NOT EXISTS SystemSettings (
    SettingId INTEGER PRIMARY KEY AUTOINCREMENT,
    SettingKey TEXT UNIQUE,
    SettingValue TEXT
)
""")

# Default maintenance mode
cursor.execute("""
INSERT OR IGNORE INTO SystemSettings (SettingKey, SettingValue)
VALUES ('MaintenanceMode', '0')
""")

conn.commit()
conn.close()

print("Database Ready Successfully")