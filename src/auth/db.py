import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "users.db"


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'citizen'")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lawyer_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                bar_council_number TEXT NOT NULL,
                practice_areas TEXT NOT NULL,
                languages TEXT NOT NULL,
                bio TEXT NOT NULL DEFAULT '',
                verification_status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS consultation_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citizen_id INTEGER NOT NULL REFERENCES users(id),
                lawyer_id INTEGER REFERENCES users(id),
                summary TEXT NOT NULL,
                details TEXT NOT NULL,
                practice_area TEXT NOT NULL,
                language TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS case_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL REFERENCES consultation_requests(id),
                sender_id INTEGER NOT NULL REFERENCES users(id),
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL REFERENCES consultation_requests(id),
                uploader_id INTEGER NOT NULL REFERENCES users(id),
                file_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                content BLOB NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL REFERENCES consultation_requests(id),
                citizen_id INTEGER NOT NULL REFERENCES users(id),
                lawyer_id INTEGER NOT NULL REFERENCES users(id),
                scheduled_for TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'requested',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


initialize_database()