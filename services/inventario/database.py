import os
import sqlite3

os.makedirs("data", exist_ok=True)
DB_NAME = "data/inventario.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL DEFAULT 5,
            proveedor TEXT NOT NULL DEFAULT 'Proveedor General'
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        productos_iniciales = [
            ("ARR-001", "Arroz 1kg", 24.50, 15, 5, "Abarrotes del Centro"),
            ("ACE-002", "Aceite 1L", 42.00, 4, 5, "Distribuidora Aceitera"),
            ("FRI-003", "Frijol Negro 1kg", 35.00, 20, 6, "Granos del Norte"),
        ]
        cursor.executemany(
            "INSERT INTO productos (sku, nombre, precio, stock, stock_minimo, proveedor) VALUES (?, ?, ?, ?, ?, ?)",
            productos_iniciales
        )
    conn.commit()
    conn.close()