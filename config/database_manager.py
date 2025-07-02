import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_description TEXT,
                timestamp TEXT NOT NULL,
                file_path TEXT NOT NULL,
                duration_seconds REAL,
                thumbnail_path TEXT
            )
        """)
        conn.commit()
        conn.close()

    def insert_event_recording(self, camera_id, event_type, event_description, timestamp, file_path, duration_seconds=None, thumbnail_path=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO event_recordings (camera_id, event_type, event_description, timestamp, file_path, duration_seconds, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (camera_id, event_type, event_description, timestamp, file_path, duration_seconds, thumbnail_path))
        conn.commit()
        conn.close()

    def get_event_recordings(self, camera_id=None, start_date=None, end_date=None, event_type=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM event_recordings WHERE 1=1"
        params = []

        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY timestamp DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

# Instancia global del gestor de base de datos
db_manager = DatabaseManager(os.path.join(os.path.dirname(__file__), 'vms_events.db'))
