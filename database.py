import sqlite3
import os
import json
import csv
from datetime import datetime
from cryptography.fernet import Fernet
from config import BASE_DIR, DB_NAME, DB_ENCRYPTION_KEY

class DataManager:
    def __init__(self):
        self.db_path = os.path.join(BASE_DIR, DB_NAME)
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
        self._init_db()
        self._check_migrations()
    
    def _get_or_create_key(self):
        key_path = os.path.join(BASE_DIR, f"{DB_ENCRYPTION_KEY}.key")
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            return key
    
    def _encrypt(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def _decrypt(self, encrypted_data):
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                settings TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Posture sessions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS posture_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                good_posture_seconds INTEGER DEFAULT 0,
                bad_posture_seconds INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Posture events table
            # Added 'feedback' column for specific error messages
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS posture_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                neck_angle REAL,
                shoulder_alignment REAL,
                spine_curvature REAL,
                is_good_posture BOOLEAN NOT NULL,
                feedback TEXT,
                FOREIGN KEY (session_id) REFERENCES posture_sessions (id)
            )
            ''')
            
            conn.commit()

    def _check_migrations(self):
        """
        Safety check: If the user has an old DB version without the 'feedback' column,
        we add it dynamically so the app doesn't crash.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # Try to select the feedback column
                cursor.execute("SELECT feedback FROM posture_events LIMIT 1")
            except sqlite3.OperationalError:
                # If it fails (column missing), add it
                print("Migrating Database: Adding feedback column...")
                cursor.execute("ALTER TABLE posture_events ADD COLUMN feedback TEXT")
                conn.commit()
    
    def create_user(self, name, settings=None):
        if settings is None:
            settings = {
                "alert_threshold": 30,
                "alert_repeat_interval": 60,
                "visual_alerts": True,
                "audio_alerts": True,
                "neck_angle_threshold": 30,
                "shoulder_alignment_threshold": 10,
                "spine_curvature_threshold": 15
            }
        
        encrypted_settings = self._encrypt(json.dumps(settings))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, settings) VALUES (?, ?)",
                (name, encrypted_settings)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_users(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users")
            return cursor.fetchall()
    
    def get_user_settings(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT settings FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                try:
                    encrypted_settings = result[0]
                    settings_json = self._decrypt(encrypted_settings)
                    return json.loads(settings_json)
                except Exception as e:
                    print(f"Error decrypting settings: {e}")
                    return None
            return None
    
    def update_user_settings(self, user_id, settings):
        encrypted_settings = self._encrypt(json.dumps(settings))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET settings = ? WHERE id = ?",
                (encrypted_settings, user_id)
            )
            conn.commit()
    
    def start_session(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO posture_sessions (user_id, start_time) VALUES (?, ?)",
                (user_id, datetime.now())
            )
            conn.commit()
            return cursor.lastrowid
    
    def end_session(self, session_id, good_posture_seconds, bad_posture_seconds):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posture_sessions SET end_time = ?, good_posture_seconds = ?, bad_posture_seconds = ? WHERE id = ?",
                (datetime.now(), good_posture_seconds, bad_posture_seconds, session_id)
            )
            conn.commit()
    
    def log_posture_event(self, session_id, timestamp, posture_data, is_good_posture):
        """
        Updated to handle dictionary input and feedback strings.
        """
        # Extract data safely from dictionary
        neck = posture_data.get('neck_angle')
        shoulder = posture_data.get('shoulder_alignment')
        spine = posture_data.get('spine_curvature')
        
        # Get feedback messages (list) and join them into a string
        msgs = posture_data.get('feedback_messages', [])
        feedback_text = "; ".join(msgs) if msgs else ""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO posture_events 
                   (session_id, timestamp, neck_angle, shoulder_alignment, spine_curvature, is_good_posture, feedback) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, timestamp, neck, shoulder, spine, is_good_posture, feedback_text)
            )
            conn.commit()
    
    def get_daily_stats(self, user_id, days=7):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DATE(start_time) as date, 
                       SUM(good_posture_seconds) as good_seconds,
                       SUM(bad_posture_seconds) as bad_seconds
                FROM posture_sessions 
                WHERE user_id = ? AND start_time >= date('now', '-{} days')
                GROUP BY DATE(start_time)
                ORDER BY date DESC
                """.format(days),
                (user_id,)
            )
            return cursor.fetchall()
    
    def delete_user_data(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Find sessions
            cursor.execute("SELECT id FROM posture_sessions WHERE user_id = ?", (user_id,))
            sessions = cursor.fetchall()
            
            # 2. Delete events for those sessions
            for (sid,) in sessions:
                cursor.execute("DELETE FROM posture_events WHERE session_id = ?", (sid,))
            
            # 3. Delete sessions
            cursor.execute("DELETE FROM posture_sessions WHERE user_id = ?", (user_id,))
            
            # 4. Delete user
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def export_data(self, user_id, output_path):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get sessions
            cursor.execute(
                "SELECT id, start_time, end_time, good_posture_seconds, bad_posture_seconds FROM posture_sessions WHERE user_id = ?",
                (user_id,)
            )
            sessions = cursor.fetchall()
            
            # Get events
            all_events = []
            for session in sessions:
                session_id = session[0]
                cursor.execute(
                    "SELECT timestamp, neck_angle, shoulder_alignment, spine_curvature, is_good_posture, feedback FROM posture_events WHERE session_id = ? ORDER BY timestamp",
                    (session_id,)
                )
                events = cursor.fetchall()
                for event in events:
                    all_events.append((session_id,) + event)
            
            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                writer.writerow(['SESSIONS'])
                writer.writerow(['Session ID', 'Start Time', 'End Time', 'Good Seconds', 'Bad Seconds'])
                writer.writerows(sessions)
                
                writer.writerow([])
                writer.writerow(['EVENTS'])
                writer.writerow(['Session ID', 'Timestamp', 'Neck Angle', 'Shoulder Angle', 'Spine Angle', 'Is Good', 'Feedback'])
                writer.writerows(all_events)