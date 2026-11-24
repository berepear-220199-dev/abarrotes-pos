import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import get_connection, init_db

app = FastAPI(title="Microservicio de Ventas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()

INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario-service:8000")
NOTIFICACIONES_URL = os.getenv("NOTIFICACIONES_URL", "http://notificaciones-service:8000")
COMPRAS_URL = os.getenv("COMPRAS_URL", "http://compras-service:8000")

class LoginRequest(BaseModel):
    username: str
    password: str

class ItemVenta(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: Optional[float] = 0

class VentaCreate(BaseModel):
    cajero: Optional[str] = "Vendedor"
    metodo_pago: Optional[str] = "Efectivo"
    items: List[ItemVenta]

@app.post("/api/login")
def login(datos: LoginRequest):
    conn = get_connection()
    user = conn.execute(
        "SELECT id, username, nombre, rol FROM usuarios WHERE username = ? AND password = ?",
        (datos.username, datos.password)
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return dict(user)

@app.get("/api/ventas")
def listar_ventas():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/ventas")
def registrar_venta(venta: VentaCreate):
    if not venta.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

    payload_inv = {"items": [{"producto_id": i.producto_id, "cantidad": i.cantidad} for i in venta.items]}
    resp_inv = requests.post(f"{INVENTARIO_URL}/api/inventario/descontar", json=payload_inv)
    if resp_inv.status_code != 200:
        raise HTTPException(status_code=resp_inv.status_code, detail=resp_inv.json().get("detail", "Error en inventario"))

    datos_inv = resp_inv.json()
    items_confirmados = datos_inv["items"]
    total = sum(i["cantidad"] * i["precio_unitario"] for i in items_confirmados)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ventas (cajero, metodo_pago, total) VALUES (?, ?, ?)",
        (venta.cajero, venta.metodo_pago, total)
    )
    venta_id = cursor.lastrowid

    for item in items_confirmados:
        cursor.execute(
            "INSERT INTO detalle_ventas (venta_id, producto_id, producto_nombre, cantidad, precio_unitario) VALUES (?, ?, ?, ?, ?)",
            (venta_id, item["producto_id"], item["nombre"], item["cantidad"], item["precio_unitario"])
        )
    conn.commit()
    conn.close()

    for alerta in datos_inv.get("bajo_stock", []):
        try:
            requests.post(f"{NOTIFICACIONES_URL}/api/notificaciones", json=alerta, timeout=3)
            requests.post(f"{COMPRAS_URL}/api/compras", json={
                "producto_id": alerta["producto_id"],
                "producto_nombre": alerta["nombre_producto"],
                "proveedor": alerta["proveedor"],
                "cantidad_sugerida": 10
            }, timeout=3)
        except requests.RequestException:
            pass

    return {"ventaId": venta_id, "total": total, "estado": "completada"}

@app.post("/api/ventas/{venta_id}/cancelar")
def cancelar_venta(venta_id: int):
    conn = get_connection()
    venta = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
    if not venta or venta["estado"] == "cancelada":
        conn.close()
        raise HTTPException(status_code=400, detail="Venta no encontrada o ya cancelada")

    detalles = conn.execute("SELECT producto_id, cantidad FROM detalle_ventas WHERE venta_id = ?", (venta_id,)).fetchall()
    items_reponer = [{"producto_id": d["producto_id"], "cantidad": d["cantidad"]} for d in detalles]

    requests.post(f"{INVENTARIO_URL}/api/inventario/reponer", json={"items": items_reponer})

    conn.execute("UPDATE ventas SET estado = 'cancelada' WHERE id = ?", (venta_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Venta cancelada y stock devuelto"}

@app.get("/api/reportes")
def obtener_reportes():
    conn = get_connection()
    hoy = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM ventas WHERE estado = 'completada' AND DATE(fecha) = DATE('now')"
    ).fetchone()[0]
    mes = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM ventas WHERE estado = 'completada' AND strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')"
    ).fetchone()[0]
    conn.close()
    return {"ingresos_hoy": hoy, "ingresos_mes": mes, "ventas_hoy": hoy, "ventas_mes": mes}