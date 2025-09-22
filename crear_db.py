import sqlite3
from datetime import datetime

conn = sqlite3.connect('basededatos.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- ELIMINAR todas las tablas si existen ---
tablas = [
    "ventas", "detalles_venta", "compras", "productos", "clientes", 
    "usuarios", "categorias", "proveedores"
]

for tabla in tablas:
    cursor.execute(f"DROP TABLE IF EXISTS {tabla};")

# --- RECREAR todas las tablas ---

cursor.execute('''
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    localidad TEXT
)
''')

cursor.execute('''
CREATE TABLE categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria_id INTEGER,
    alto REAL,
    ancho REAL,
    profundidad REAL,
    precio REAL,
    foto TEXT,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
)
''')

cursor.execute('''
CREATE TABLE proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT
)
''')

cursor.execute('''
CREATE TABLE compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER REFERENCES proveedores(id),
    producto_id INTEGER REFERENCES productos(id),
    cantidad INTEGER,
    precio_unitario REAL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    producto_id INTEGER,
    cantidad INTEGER,
    total REAL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
)
''')

cursor.execute('''
CREATE TABLE detalles_venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER REFERENCES ventas(id),
    producto_id INTEGER REFERENCES productos(id),
    cantidad INTEGER,
    precio_unitario REAL,
    total REAL
)
''')

cursor.execute('''
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT UNIQUE,
    contraseña TEXT NOT NULL,
    rol TEXT CHECK(rol IN ('admin', 'vendedor')) NOT NULL
)
''')

# --- Consulta de ventas (solo si hay datos) ---
try:
    cursor.execute('''
    SELECT v.id, c.nombre AS cliente, p.nombre AS producto, v.cantidad, v.total, v.fecha
    FROM ventas v
    JOIN clientes c ON v.cliente_id = c.id
    JOIN productos p ON v.producto_id = p.id
    ORDER BY v.fecha DESC
    ''')
    ventas = cursor.fetchall()

    ventas_convertidas = []
    for venta in ventas:
        venta_dict = dict(venta)
        venta_dict['fecha'] = datetime.strptime(venta_dict['fecha'], '%Y-%m-%d %H:%M:%S')
        ventas_convertidas.append(venta_dict)

except sqlite3.OperationalError:
    ventas_convertidas = []
    print("No se pudieron consultar ventas: aún no hay datos.")

conn.commit()
conn.close()

print("Base de datos reiniciada correctamente. Todas las tablas fueron recreadas.")
