from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection, init_db

app = FastAPI(title="Microservicio de Compras")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()

class OrdenCompraCreate(BaseModel):
    producto_id: int
    producto_nombre: str
    proveedor: str
    cantidad_sugerida: int = 10

@app.get("/api/compras")
def listar_compras():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM compras_pendientes ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/compras")
def generar_orden_compra(orden: OrdenCompraCreate):
    conn = get_connection()
    cursor = conn.cursor()

    existente = cursor.execute(
        "SELECT id FROM compras_pendientes WHERE producto_id = ? AND estado = 'pendiente'",
        (orden.producto_id,)
    ).fetchone()

    if existente:
        conn.close()
        return {"ordenId": existente["id"], "estado": "ya existe en lista de reabastecimiento"}

    cursor.execute(
        "INSERT INTO compras_pendientes (producto_id, producto_nombre, proveedor, cantidad_sugerida) VALUES (?, ?, ?, ?)",
        (orden.producto_id, orden.producto_nombre, orden.proveedor, orden.cantidad_sugerida)
    )
    orden_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"ordenId": orden_id, "estado": "agregado a lista de reabastecimiento"}