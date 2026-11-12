import os
import sqlite3

os.makedirs("data", exist_ok=True)
DB_NAME = "data/abarrotes.db"
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Tabla Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre TEXT NOT NULL,
        rol TEXT NOT NULL CHECK(rol IN ('administrador', 'vendedor'))
    )
    """)

    # 2. Tabla Productos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        precio_unitario REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        stock_minimo INTEGER NOT NULL DEFAULT 5,
        proveedor TEXT NOT NULL,
        imagen_url TEXT
    )
    """)

    # 3. Tabla Ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        cajero TEXT NOT NULL,
        metodo_pago TEXT NOT NULL DEFAULT 'Efectivo',
        total REAL NOT NULL,
        estado TEXT NOT NULL DEFAULT 'completada' CHECK(estado IN ('completada', 'cancelada'))
    )
    """)

    # 4. Tabla Detalle de Ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalle_ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio_unitario REAL NOT NULL,
        FOREIGN KEY (venta_id) REFERENCES ventas(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    """)

    # 5. Tabla Notificaciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notificaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        mensaje TEXT NOT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    """)

    # 6. Tabla Compras Pendientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras_pendientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        cantidad_sugerida INTEGER NOT NULL DEFAULT 10,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    """)

    # Insertar usuarios base si no existen
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (usuario, password, nombre, rol) VALUES ('admin', '1234', 'Administrador General', 'administrador')")
        cursor.execute("INSERT INTO usuarios (usuario, password, nombre, rol) VALUES ('vendedor', '1234', 'Cajero Turno 1', 'vendedor')")

    # Insertar productos de prueba si está vacía
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO productos (sku, nombre, precio_unitario, stock, stock_minimo, proveedor) VALUES ('75010001', 'Leche Entera 1L', 27.50, 15, 5, 'Lala')")
        cursor.execute("INSERT INTO productos (sku, nombre, precio_unitario, stock, stock_minimo, proveedor) VALUES ('75010002', 'Pan Blanco Grande', 45.00, 8, 3, 'Bimbo')")
        cursor.execute("INSERT INTO productos (sku, nombre, precio_unitario, stock, stock_minimo, proveedor) VALUES ('75010003', 'Refresco Cola 600ml', 18.00, 4, 6, 'Coca-Cola')")

    conn.commit()
    conn.close()