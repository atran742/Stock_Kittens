import sqlite3
import json

class StockChatMemory:
    def __init__(self, db_path="trading_agent.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        # We store the role (user/assistant) and the message content
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def save_message(self, session_id, role, content):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        self.conn.commit()

    def get_history(self, session_id, limit=10):
        cursor = self.conn.cursor()
        # Fetch the last 'limit' messages to keep the context window manageable
        cursor.execute("""
            SELECT role, content FROM (
                SELECT role, content, id FROM chat_history 
                WHERE session_id = ? 
                ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
        """, (session_id, limit))
        return cursor.fetchall()