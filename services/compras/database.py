import os
import sqlite3

os.makedirs("data", exist_ok=True)
DB_NAME = "data/compras.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compras_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            producto_nombre TEXT NOT NULL,
            proveedor TEXT NOT NULL,
            cantidad_sugerida INTEGER NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()