const API_URL = "http://127.0.0.1:8000/api";

let currentUser = null;
let productosCache = [];
let cart = [];

// --- PERSISTENCIA EN EL LOGIN ---
window.addEventListener("DOMContentLoaded", () => {
    const sesion = localStorage.getItem("usuario_sesion");
    if (sesion) {
        currentUser = JSON.parse(sesion);
        iniciarSesionUI();
    } else {
        mostrarVista("login");
    }
});

function mostrarVista(vista) {
    document.getElementById("view-login").classList.add("hidden");
    document.getElementById("view-pos").classList.add("hidden");
    document.getElementById("view-admin").classList.add("hidden");
    document.getElementById("navbar").classList.add("hidden");

    if (vista === "login") {
        document.getElementById("view-login").classList.remove("hidden");
    } else if (vista === "app") {
        document.getElementById("navbar").classList.remove("hidden");
        document.getElementById("view-pos").classList.remove("hidden");
        if (currentUser.rol === "administrador") {
            document.getElementById("view-admin").classList.remove("hidden");
        }
    }
}

// --- LOGIN Y SESIÓN ---
async function realizarLogin(event) {
    if (event) event.preventDefault();
    
    const usuarioInput = document.getElementById("login-usuario").value;
    const passwordInput = document.getElementById("login-password").value;
    const errorDiv = document.getElementById("login-error");

    errorDiv.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario: usuarioInput, password: passwordInput })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Error al iniciar sesión");
        }

        currentUser = await response.json();
        localStorage.setItem("usuario_sesion", JSON.stringify(currentUser));
        iniciarSesionUI();
    } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.classList.remove("hidden");
    }
}

function iniciarSesionUI() {
    document.getElementById("user-display").textContent = `${currentUser.nombre} (${currentUser.rol.toUpperCase()})`;
    mostrarVista("app");
    cargarProductos();
    cargarHistorialVentas();
    if (currentUser.rol === "administrador") {
        cargarPanelAdmin();
    }
}

function cerrarSesion() {
    localStorage.removeItem("usuario_sesion");
    currentUser = null;
    cart = [];
    mostrarVista("login");
}

// --- CATALOGO Y CARRITO ---
async function cargarProductos() {
    try {
        const res = await fetch(`${API_URL}/productos`);
        productosCache = await res.json();
        renderProductosGrid(productosCache);
    } catch (err) {
        console.error("Error al cargar productos:", err);
    }
}

function renderProductosGrid(lista) {
    const grid = document.getElementById("pos-productos-grid");
    grid.innerHTML = "";

    lista.forEach(p => {
        const item = document.createElement("div");
        item.className = `product-card ${p.stock <= p.stock_minimo ? 'low-stock' : ''}`;
        item.innerHTML = `
            <h4>${p.nombre}</h4>
            <p>SKU: ${p.sku}</p>
            <p class="price">$${p.precio_unitario.toFixed(2)}</p>
            <p class="stock">Stock: ${p.stock} pzas</p>
            <button type="button" class="btn-primary" onclick="agregarAlCarrito(${p.id})">Agregar</button>
        `;
        grid.appendChild(item);
    });
}

function filtrarProductos() {
    const q = document.getElementById("search-prod").value.toLowerCase();
    const filtrados = productosCache.filter(p => p.nombre.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q));
    renderProductosGrid(filtrados);
}

function agregarAlCarrito(prodId) {
    const prod = productosCache.find(p => p.id === prodId);
    if (!prod || prod.stock <= 0) {
        alert("Producto sin stock disponible");
        return;
    }

    const itemEnCarrito = cart.find(c => c.producto_id === prodId);
    if (itemEnCarrito) {
        if (itemEnCarrito.cantidad + 1 > prod.stock) {
            alert("No hay suficiente stock disponible");
            return;
        }
        itemEnCarrito.cantidad++;
    } else {
        cart.push({
            producto_id: prod.id,
            nombre: prod.nombre,
            precio_unitario: prod.precio_unitario,
            cantidad: 1
        });
    }

    actualizarCarritoUI();
}

function actualizarCarritoUI() {
    const tbody = document.getElementById("cart-table-body");
    tbody.innerHTML = "";
    let total = 0;

    cart.forEach((item, index) => {
        const subtotal = item.cantidad * item.precio_unitario;
        total += subtotal;

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.nombre}</td>
            <td>${item.cantidad}</td>
            <td>$${item.precio_unitario.toFixed(2)}</td>
            <td>$${subtotal.toFixed(2)}</td>
            <td><button type="button" class="btn-danger-sm" onclick="quitarDelCarrito(${index})">X</button></td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById("cart-total").textContent = total.toFixed(2);
}

function quitarDelCarrito(index) {
    cart.splice(index, 1);
    actualizarCarritoUI();
}

// --- PROCESAR Y CANCELAR VENTAS ---
async function procesarVenta(event) {
    if (event) event.preventDefault();

    if (cart.length === 0) {
        alert("El carrito está vacío");
        return;
    }

    const payload = {
        cajero: currentUser.nombre,
        metodo_pago: "Efectivo",
        items: cart.map(i => ({
            producto_id: i.producto_id,
            cantidad: i.cantidad,
            precio_unitario: i.precio_unitario
        }))
    };

    try {
        const res = await fetch(`${API_URL}/ventas`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al procesar la venta");
        }

        alert("Venta registrada con éxito");
        cart = [];
        actualizarCarritoUI();
        cargarProductos();
        cargarHistorialVentas();
        if (currentUser.rol === "administrador") cargarPanelAdmin();
    } catch (err) {
        alert(err.message);
    }
}

async function cargarHistorialVentas() {
    try {
        const res = await fetch(`${API_URL}/ventas`);
        const ventas = await res.json();

        const tbody = document.getElementById("sales-history-body");
        tbody.innerHTML = "";

        ventas.slice(0, 5).forEach(v => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>#${v.id}</td>
                <td>${v.fecha}</td>
                <td>${v.cajero}</td>
                <td>$${v.total.toFixed(2)}</td>
                <td><span class="badge ${v.estado}">${v.estado}</span></td>
                <td>
                    ${v.estado === 'completada' ? `<button type="button" class="btn-danger-sm" onclick="cancelarVenta(${v.id})">Cancelar</button>` : '-'}
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error("Error al cargar historial:", err);
    }
}

async function cancelarVenta(ventaId) {
    if (!confirm("¿Deseas cancelar esta venta y devolver el stock?")) return;

    try {
        const res = await fetch(`${API_URL}/ventas/${ventaId}/cancelar`, { method: "POST" });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail);
        }
        alert("Venta cancelada exitosamente");
        cargarProductos();
        cargarHistorialVentas();
        if (currentUser.rol === "administrador") cargarPanelAdmin();
    } catch (err) {
        alert(err.message);
    }
}

// --- ADMINISTRACIÓN ---
async function agregarNuevoProducto(event) {
    if (event) event.preventDefault();

    const payload = {
        sku: document.getElementById("prod-sku").value,
        nombre: document.getElementById("prod-nombre").value,
        precio_unitario: parseFloat(document.getElementById("prod-precio").value),
        stock: parseInt(document.getElementById("prod-stock").value),
        stock_minimo: parseInt(document.getElementById("prod-stock-min").value),
        proveedor: document.getElementById("prod-proveedor").value
    };

    try {
        const res = await fetch(`${API_URL}/productos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail);
        }

        alert("Producto agregado correctamente");
        event.target.reset();
        cargarProductos();
    } catch (err) {
        alert(err.message);
    }
}

async function cargarPanelAdmin() {
    try {
        const [repRes, notifRes, compRes] = await Promise.all([
            fetch(`${API_URL}/reportes`),
            fetch(`${API_URL}/notificaciones`),
            fetch(`${API_URL}/compras`)
        ]);

        const rep = await repRes.json();
        document.getElementById("metric-dia").textContent = rep.total_diario.toFixed(2);
        document.getElementById("metric-mes").textContent = rep.total_mensual.toFixed(2);

        const notifs = await notifRes.json();
        const notifUl = document.getElementById("notif-list");
        notifUl.innerHTML = notifs.length === 0 ? "<li>Sin alertas de bajo stock</li>" : "";
        notifs.forEach(n => {
            const li = document.createElement("li");
            li.textContent = ` ${n.mensaje} (${n.fecha})`;
            notifUl.appendChild(li);
        });

        const compras = await compRes.json();
        const compTbody = document.getElementById("reorder-table-body");
        compTbody.innerHTML = "";
        compras.forEach(c => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${c.sku}</td>
                <td>${c.nombre}</td>
                <td>${c.proveedor}</td>
                <td><strong>+${c.cantidad_sugerida}</strong></td>
            `;
            compTbody.appendChild(row);
        });

    } catch (err) {
        console.error("Error al cargar panel de admin:", err);
    }
}