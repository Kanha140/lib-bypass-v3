import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import config

DB_FILE = os.path.join(os.path.dirname(__file__), "bot_database.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Reseller table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resellers (
                user_id INTEGER PRIMARY KEY,
                credits INTEGER NOT NULL DEFAULT 0,
                added_by INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Keys History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keys_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                license_key TEXT,
                username TEXT,
                days INTEGER NOT NULL,
                credits_spent INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)
        conn.commit()


def is_owner(user_id: int) -> bool:
    return int(user_id) == int(config.OWNER_ID)


def is_reseller(user_id: int) -> bool:
    if is_owner(user_id):
        return True
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM resellers WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None


def get_credits(user_id: int) -> int:
    if is_owner(user_id):
        return 999999  # Unlimited for owner
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT credits FROM resellers WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row["credits"] if row else 0


def add_reseller(user_id: int, credits: int = 0, added_by: int = 0) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resellers (user_id, credits, added_by)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                credits = credits + excluded.credits
        """, (user_id, credits, added_by))
        conn.commit()
        return True


def remove_reseller(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resellers WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def add_credits(user_id: int, amount: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resellers (user_id, credits)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                credits = credits + excluded.credits
        """, (user_id, amount))
        conn.commit()
        cursor.execute("SELECT credits FROM resellers WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row["credits"] if row else amount


def deduct_credits(user_id: int, amount: int) -> bool:
    if is_owner(user_id):
        return True  # Owner does not spend limited balance

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT credits FROM resellers WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        current_credits = row["credits"]
        if current_credits < amount:
            return False

        cursor.execute(
            "UPDATE resellers SET credits = credits - ? WHERE user_id = ?",
            (amount, user_id)
        )
        conn.commit()
        return True


def refund_credits(user_id: int, amount: int):
    if is_owner(user_id):
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE resellers SET credits = credits + ? WHERE user_id = ?",
            (amount, user_id)
        )
        conn.commit()


def record_generated_key(user_id: int, license_key: str, username: str, days: int, credits_spent: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO keys_history (user_id, license_key, username, days, credits_spent)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, license_key, username, days, credits_spent))
        conn.commit()


def get_user_keys(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_owner(user_id):
            cursor.execute("""
                SELECT * FROM keys_history
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT * FROM keys_history
                WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
            """, (user_id, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_all_user_active_keys(user_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM keys_history
            WHERE user_id = ? AND status != 'DELETED'
            ORDER BY id DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_all_user_keys_db(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE keys_history
            SET status = 'DELETED'
            WHERE user_id = ? AND status != 'DELETED'
        """, (user_id,))
        conn.commit()
        return cursor.rowcount


def mark_key_deleted(key_or_user: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE keys_history
            SET status = 'DELETED'
            WHERE license_key = ? OR username = ?
        """, (key_or_user, key_or_user))
        conn.commit()
        return cursor.rowcount > 0


# Initialize database upon import
init_db()
