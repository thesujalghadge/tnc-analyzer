import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/tnc_analyzer.db")


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                source_type TEXT NOT NULL,
                original_name TEXT,
                source_url TEXT,
                stored_path TEXT,
                file_size INTEGER,
                page_count INTEGER NOT NULL,
                mime_type TEXT,
                checksum TEXT,
                extra_metadata TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
                summary TEXT NOT NULL,
                formatted_output TEXT NOT NULL,
                risk_overview_json TEXT NOT NULL,
                model_used TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                text TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analysis_clauses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
                chunk_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                clause_text TEXT NOT NULL,
                category TEXT NOT NULL,
                category_confidence REAL NOT NULL,
                risk TEXT NOT NULL,
                risk_score REAL NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT NOT NULL,
                highlighted_terms_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                grounded INTEGER NOT NULL,
                confidence REAL NOT NULL,
                citations_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_documents_user_created_at
            ON documents(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
            ON auth_sessions(user_id, expires_at DESC);

            CREATE INDEX IF NOT EXISTS idx_chunks_document
            ON document_chunks(document_id, chunk_id);

            CREATE INDEX IF NOT EXISTS idx_clauses_analysis
            ON analysis_clauses(analysis_id, risk_score DESC);

            CREATE INDEX IF NOT EXISTS idx_chat_document
            ON chat_history(document_id, created_at DESC);
            """
        )
