import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

def get_db_connection():
    """
    Create a PostgreSQL database connection using environment variables.

    Required environment variables:
    - DB_HOST: Database host (e.g., db.xxx.supabase.co)
    - DB_PORT: Database port (default: 5432)
    - DB_NAME: Database name (default: postgres)
    - DB_USER: Database user (default: postgres)
    - DB_PASSWORD: Database password
    """

    # Get environment variables with defaults
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'postgres')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')

    # Validate required variables
    if not db_host:
        raise ValueError("DB_HOST environment variable is required")
    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required")

    # Build connection URL
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    try:
        connection = psycopg2.connect(database_url)
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        print(f"Connection details: host={db_host}, port={db_port}, database={db_name}, user={db_user}")
        raise
    

