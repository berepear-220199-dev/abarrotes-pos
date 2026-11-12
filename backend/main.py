from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.database import init_db, get_connection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class LoginRequest(BaseModel):
    usuario: str
    password: str

class ItemVenta(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: float

class RegistrarVentaRequest(BaseModel):
    cajero: str
    metodo_pago: str = "Efectivo"
    items: list[ItemVenta]

class ProductoRequest(BaseModel):
    sku: str
    nombre: str
    precio_unitario: float
    stock: int
    stock_minimo: int
    proveedor: str
    imagen_url: str = "https://via.placeholder.com/150"

@app.post("/api/login")
def login(data: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario, nombre, rol FROM usuarios WHERE usuario = ? AND password = ?", (data.usuario, data.password))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    return {
        "status": "ok",
        "usuario": user["usuario"],
        "nombre": user["nombre"],
        "rol": user["rol"]
    }

@app.get("/api/productos")
def listar_productos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

@app.post("/api/productos")
def agregar_producto(prod: ProductoRequest):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO productos (sku, nombre, precio_unitario, stock, stock_minimo, proveedor, imagen_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (prod.sku, prod.nombre, prod.precio_unitario, prod.stock, prod.stock_minimo, prod.proveedor, prod.imagen_url)
        )
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="El SKU ya existe o los datos son inválidos")
    conn.close()
    return {"status": "ok", "mensaje": "Producto agregado con éxito"}

@app.delete("/api/productos/{producto_id}")
def eliminar_producto(producto_id: int, rol: str):
    if rol != "administrador":
        raise HTTPException(status_code=403, detail="Solo el administrador puede eliminar productos")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "mensaje": "Producto eliminado"}

@app.post("/api/ventas")
def registrar_venta(venta: RegistrarVentaRequest):
    conn = get_connection()
    cursor = conn.cursor()

    total_calculado = 0
    for item in venta.items:
        cursor.execute("SELECT stock, nombre FROM productos WHERE id = ?", (item.producto_id,))
        prod = cursor.fetchone()
        if not prod or prod["stock"] < item.cantidad:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para: {prod['nombre'] if prod else 'Producto'}")
        total_calculado += item.cantidad * item.precio_unitario

    cursor.execute("INSERT INTO ventas (cajero, metodo_pago, total, estado) VALUES (?, ?, ?, 'completada')",
                   (venta.cajero, venta.metodo_pago, total_calculado))
    venta_id = cursor.lastrowid

    for item in venta.items:
        cursor.execute("INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                       (venta_id, item.producto_id, item.cantidad, item.precio_unitario))
        
        cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item.cantidad, item.producto_id))

        cursor.execute("SELECT id, nombre, stock, stock_minimo, proveedor FROM productos WHERE id = ?", (item.producto_id,))
        prod_actual = cursor.fetchone()

        if prod_actual["stock"] <= prod_actual["stock_minimo"]:
            msg = f"Solo quedan {prod_actual['stock']} unidades de {prod_actual['nombre']}"
            cursor.execute("INSERT INTO notificaciones (producto_id, mensaje) VALUES (?, ?)", (item.producto_id, msg))
            cursor.execute("INSERT INTO compras_pendientes (producto_id, cantidad_sugerida) VALUES (?, 10)", (item.producto_id,))

    conn.commit()
    conn.close()
    return {"status": "ok", "venta_id": venta_id, "total": total_calculado}

@app.post("/api/ventas/{venta_id}/cancelar")
def cancelar_venta(venta_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT estado FROM ventas WHERE id = ?", (venta_id,))
    v = cursor.fetchone()
    if not v:
        conn.close()
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if v["estado"] == "cancelada":
        conn.close()
        raise HTTPException(status_code=400, detail="La venta ya estaba cancelada")

    cursor.execute("SELECT producto_id, cantidad FROM detalle_ventas WHERE venta_id = ?", (venta_id,))
    detalles = cursor.fetchall()
    for item in detalles:
        cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (item["cantidad"], item["producto_id"]))

    cursor.execute("UPDATE ventas SET estado = 'cancelada' WHERE id = ?", (venta_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "mensaje": "Venta cancelada exitosamente y stock restaurado"}

@app.get("/api/ventas")
def listar_ventas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
    ventas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ventas

@app.get("/api/notificaciones")
def obtener_notificaciones():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT n.id, n.mensaje, n.fecha, p.nombre, p.stock FROM notificaciones n JOIN productos p ON n.producto_id = p.id ORDER BY n.id DESC LIMIT 10")
    alertas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return alertas

@app.get("/api/compras")
def obtener_lista_compras():
    conn = get_connection()
    cursor = conn.cursor()
    sql = """SELECT c.id, p.sku, p.nombre, p.proveedor, c.cantidad_sugerida, c.fecha 
             FROM compras_pendientes c 
             JOIN productos p ON c.producto_id = p.id 
             WHERE c.estado = 'pendiente' GROUP BY p.id"""
    cursor.execute(sql)
    compras = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return compras

@app.get("/api/reportes")
def obtener_reportes():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(total) FROM ventas WHERE estado = 'completada' AND DATE(fecha) = DATE('now', 'localtime')")
    dia = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(total) FROM ventas WHERE estado = 'completada' AND strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now', 'localtime')")
    mes = cursor.fetchone()[0] or 0.0

    conn.close()
    return {"total_diario": dia, "total_mensual": mes}