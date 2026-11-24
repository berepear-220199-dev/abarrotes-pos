from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection, init_db

app = FastAPI(title="Microservicio de Notificaciones")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()

class AlertaCreate(BaseModel):
    producto_id: int
    nombre_producto: str
    stock_actual: int
    stock_minimo: int

@app.get("/api/notificaciones")
def listar_notificaciones():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM notificaciones ORDER BY id DESC LIMIT 15").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/notificaciones")
def crear_notificacion(alerta: AlertaCreate):
    mensaje = f"⚠️ Solo quedan {alerta.stock_actual} unidades de {alerta.nombre_producto} (Mínimo: {alerta.stock_minimo})"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notificaciones (producto_id, mensaje) VALUES (?, ?)",
        (alerta.producto_id, mensaje)
    )
    alerta_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"alertaId": alerta_id, "estado": "mostrada en pantalla", "mensaje": mensaje}