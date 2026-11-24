import os
import sqlite3

os.makedirs("data", exist_ok=True)
DB_NAME = "data/ventas.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT NOT NULL,
            metodo_pago TEXT DEFAULT 'Efectivo',
            total REAL NOT NULL,
            estado TEXT DEFAULT 'completada'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            producto_nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
            [
                ("admin", "1234", "Administrador General", "administrador"),
                ("vendedor", "1234", "Vendedor Juan", "vendedor"),
            ]
        )
    conn.commit()
    conn.close()