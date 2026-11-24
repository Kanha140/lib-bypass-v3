import os
import sys
import json
import base64
import time
import sqlite3
import threading
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GH_TOKEN = os.getenv("GH_TOKEN", "")
REPO = os.getenv("GH_REPO", "Kanha140/lib-bypass-v3")
BRANCH = os.getenv("GH_BRANCH", "db-data")

class CloudSync:
    def __init__(self, db_file_path: str):
        self.db_file_path = db_file_path
        self.db_name = os.path.basename(db_file_path)
        self.json_filename = f"{os.path.splitext(self.db_name)[0]}.json"
        self._dirty = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._headers = {
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        # Start background sync thread
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def mark_dirty(self):
        with self._lock:
            self._dirty = True

    def export_to_dict(self) -> dict:
        if not os.path.exists(self.db_file_path):
            return {}
        try:
            conn = sqlite3.connect(self.db_file_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Export resellers
            resellers = []
            try:
                cur.execute("SELECT user_id, credits, added_by, created_at FROM resellers")
                for r in cur.fetchall():
                    resellers.append({
                        "user_id": r["user_id"],
                        "credits": r["credits"],
                        "added_by": r["added_by"],
                        "created_at": str(r["created_at"])
                    })
            except Exception:
                pass

            # Export keys_history
            keys_history = []
            try:
                cur.execute("SELECT id, user_id, license_key, username, days, credits_spent, created_at, status FROM keys_history")
                for k in cur.fetchall():
                    keys_history.append({
                        "id": k["id"],
                        "user_id": k["user_id"],
                        "license_key": k["license_key"],
                        "username": k["username"],
                        "days": k["days"],
                        "credits_spent": k["credits_spent"],
                        "created_at": str(k["created_at"]),
                        "status": k["status"]
                    })
            except Exception:
                pass

            conn.close()
            return {"resellers": resellers, "keys_history": keys_history, "updated_at": time.time()}
        except Exception as e:
            print(f"[CloudSync] Export error for {self.db_name}: {e}", flush=True)
            return {}

    def restore_from_cloud(self):
        """
        Pulls latest JSON state from GitHub branch and merges into local SQLite DB.
        """
        if not GH_TOKEN:
            print("[CloudSync] No GH_TOKEN provided; skipping cloud restore.", flush=True)
            return

        url = f"https://api.github.com/repos/{REPO}/contents/{self.json_filename}?ref={BRANCH}"
        data = None
        for attempt in range(3):
            try:
                r = requests.get(url, headers=self._headers, timeout=12)
                if r.status_code == 200:
                    content_b64 = r.json()["content"]
                    content_str = base64.b64decode(content_b64).decode("utf-8")
                    data = json.loads(content_str)
                    break
                elif r.status_code == 404:
                    print(f"[CloudSync] No cloud backup found for {self.json_filename} (attempt {attempt+1})", flush=True)
                    # If no cloud backup, push initial local data to cloud
                    self.mark_dirty()
                    return
            except Exception as e:
                print(f"[CloudSync] Restore attempt {attempt+1} failed: {e}", flush=True)
                time.sleep(2)

        if not data:
            return

        try:
            conn = sqlite3.connect(self.db_file_path)
            cur = conn.cursor()

            # Ensure tables exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resellers (
                    user_id INTEGER PRIMARY KEY,
                    credits INTEGER NOT NULL DEFAULT 0,
                    added_by INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
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

            # Merge resellers
            resellers = data.get("resellers", [])
            for r in resellers:
                cur.execute("""
                    INSERT INTO resellers (user_id, credits, added_by, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        credits = excluded.credits,
                        added_by = excluded.added_by
                """, (r["user_id"], r["credits"], r.get("added_by", 0), r.get("created_at")))

            # Merge keys_history
            keys = data.get("keys_history", [])
            for k in keys:
                cur.execute("""
                    INSERT OR IGNORE INTO keys_history (id, user_id, license_key, username, days, credits_spent, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (k.get("id"), k["user_id"], k["license_key"], k.get("username", ""), k["days"], k["credits_spent"], k.get("created_at"), k.get("status", "ACTIVE")))

            conn.commit()
            conn.close()
            print(f"[CloudSync] Successfully restored {len(resellers)} resellers and {len(keys)} keys into {self.db_name}", flush=True)
        except Exception as e:
            print(f"[CloudSync] Error applying restored data to {self.db_name}: {e}", flush=True)

    def push_to_cloud(self) -> bool:
        if not GH_TOKEN:
            return False

        payload_dict = self.export_to_dict()
        if not payload_dict:
            return False

        content_str = json.dumps(payload_dict, indent=2)
        b64_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        url = f"https://api.github.com/repos/{REPO}/contents/{self.json_filename}"

        for attempt in range(3):
            try:
                # Get existing file sha
                r = requests.get(f"{url}?ref={BRANCH}", headers=self._headers, timeout=12)
                body = {
                    "message": f"CloudSync backup for {self.db_name}",
                    "content": b64_content,
                    "branch": BRANCH
                }
                if r.status_code == 200 and "sha" in r.json():
                    body["sha"] = r.json()["sha"]

                put_r = requests.put(url, headers=self._headers, json=body, timeout=12)
                if put_r.status_code in [200, 201]:
                    print(f"[CloudSync] Successfully synced {self.db_name} to cloud ({put_r.status_code})", flush=True)
                    return True
                else:
                    print(f"[CloudSync] Push attempt {attempt+1} failed: {put_r.status_code} {put_r.text[:100]}", flush=True)
            except Exception as e:
                print(f"[CloudSync] Push attempt {attempt+1} error: {e}", flush=True)
            time.sleep(2)
        return False

    def _worker_loop(self):
        while not self._stop_event.is_set():
            time.sleep(5)
            should_sync = False
            with self._lock:
                if self._dirty:
                    should_sync = True
                    self._dirty = False

            if should_sync:
                try:
                    self.push_to_cloud()
                except Exception as e:
                    print(f"[CloudSync] Worker sync error: {e}", flush=True)
