from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from database import get_connection, init_db

app = FastAPI(title="Microservicio de Inventario")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()

class ProductoCreate(BaseModel):
    sku: str
    nombre: str
    precio: float
    stock: int
    stock_minimo: int = 5
    proveedor: str = "Proveedor General"

class ItemMovimiento(BaseModel):
    producto_id: int
    cantidad: int

class MovimientoRequest(BaseModel):
    items: List[ItemMovimiento]

@app.get("/api/productos")
def listar_productos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/productos")
def crear_producto(prod: ProductoCreate):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO productos (sku, nombre, precio, stock, stock_minimo, proveedor) VALUES (?, ?, ?, ?, ?, ?)",
            (prod.sku, prod.nombre, prod.precio, prod.stock, prod.stock_minimo, prod.proveedor)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Error al crear producto: {str(e)}")
    conn.close()
    return {"mensaje": "Producto registrado en inventario"}

@app.delete("/api/productos/{producto_id}")
def eliminar_producto(producto_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Producto eliminado"}

@app.post("/api/inventario/descontar")
def descontar_stock(req: MovimientoRequest):
    conn = get_connection()
    cursor = conn.cursor()
    detalles_confirmados = []
    alertas_bajo_stock = []

    for item in req.items:
        prod = cursor.execute("SELECT * FROM productos WHERE id = ?", (item.producto_id,)).fetchone()
        if not prod:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Producto ID {item.producto_id} no encontrado")
        if prod["stock"] < item.cantidad:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para {prod['nombre']}")

    for item in req.items:
        prod = cursor.execute("SELECT * FROM productos WHERE id = ?", (item.producto_id,)).fetchone()
        nuevo_stock = prod["stock"] - item.cantidad
        cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, item.producto_id))
        detalles_confirmados.append({
            "producto_id": prod["id"],
            "nombre": prod["nombre"],
            "cantidad": item.cantidad,
            "precio_unitario": prod["precio"]
        })
        if nuevo_stock <= prod["stock_minimo"]:
            alertas_bajo_stock.append({
                "producto_id": prod["id"],
                "nombre_producto": prod["nombre"],
                "stock_actual": nuevo_stock,
                "stock_minimo": prod["stock_minimo"],
                "proveedor": prod["proveedor"]
            })

    conn.commit()
    conn.close()
    return {"disponible": True, "items": detalles_confirmados, "bajo_stock": alertas_bajo_stock}

@app.post("/api/inventario/reponer")
def reponer_stock(req: MovimientoRequest):
    conn = get_connection()
    for item in req.items:
        conn.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (item.cantidad, item.producto_id))
    conn.commit()
    conn.close()
    return {"mensaje": "Stock restaurado"}