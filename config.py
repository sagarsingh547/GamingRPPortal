class Config:
    SECRET_KEY = 'super_secret_gaming_key'
    
    # Aapka exact SQL Server name screenshot se:
    SERVER = r'LAPTOP-FT6PBDV8\SQLEXPRESS' 
    DATABASE = 'GamingRPPortalDB'
    
    # Windows Authentication connection string
    DB_CONNECTION_STRING = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"