
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
import os
from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from flask import make_response
import io
import pandas as pd
from flask import jsonify
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from types import SimpleNamespace

def get_db_connection():
    conn = sqlite3.connect('basededatos.db')
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)
app.secret_key = 'clave-secreta-segura'  # Cambia esto por algo seguro

# Configuración de carpeta para subir imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crea la carpeta si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Usuario de prueba
USUARIO = {
    'username': 'admin',
    'password': '1234'
}

# Función decoradora para proteger rutas
def login_required(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if 'usuario' not in session:
            flash("Por favor iniciá sesión para continuar", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorada

@app.route('/inicio')
@login_required
def inicio():
    datos_ventas = [12, 19, 15, 8, 10, 14]  # datos dinámicos
    return render_template('inicio.html', ventas=datos_ventas)

@app.route('/home')
@login_required
def home():
    return render_template('home.html', usuario=session['usuario'])

@app.route('/', methods=['GET', 'POST'])  # Página de inicio y login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        contraseña = request.form['password']

        # Validación sencilla
        if usuario == 'admin' and contraseña == '1234':
            session['usuario'] = usuario
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for('home'))  # Redirige a /home
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('usuario', None)
    flash("Sesión cerrada", "info")
    return redirect(url_for('login'))

@app.route('/clientes')
@login_required
def clientes():
    conn = get_db_connection()
    clientes = conn.execute('SELECT * FROM clientes').fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

from flask import request, redirect, url_for, flash

@app.route('/agregar_cliente', methods=['POST'])
def agregar_cliente():
    nombre = request.form['nombre'].strip()
    telefono = request.form['telefono'].strip()
    email = request.form['email'].strip()
    localidad = request.form['localidad'].strip()
    fecha_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # << línea nueva

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO clientes (nombre, telefono, email, localidad, fecha_registro) VALUES (?, ?, ?, ?, ?)',
            (nombre, telefono, email, localidad, fecha_registro)  # << se agrega fecha
        )
        conn.commit()
        conn.close()
        flash('Cliente agregado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al agregar cliente: {e}', 'danger')

    return redirect(url_for('clientes'))


@app.route('/clientes/editar/<int:cliente_id>', methods=['GET'])
@login_required
def editar_cliente(cliente_id):
    conn = get_db_connection()
    cliente = conn.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
    conn.close()
    if cliente is None:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('clientes'))
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/clientes/editar/<int:cliente_id>', methods=['POST'])
@login_required
def actualizar_cliente(cliente_id):
    nombre = request.form['nombre'].strip()
    telefono = request.form['telefono'].strip()
    email = request.form['email'].strip()
    localidad = request.form['localidad'].strip()

    if not nombre:
        flash('El nombre es obligatorio.', 'danger')
        return redirect(url_for('editar_cliente', cliente_id=cliente_id))

    conn = get_db_connection()
    conn.execute('UPDATE clientes SET nombre = ?, telefono = ?, email = ?, localidad = ? WHERE id = ?',
                 (nombre, telefono, email, localidad, cliente_id))
    conn.commit()
    conn.close()

    flash('Cliente actualizado correctamente', 'success')
    return redirect(url_for('clientes'))


@app.route('/clientes/eliminar/<int:cliente_id>', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
    conn.commit()
    conn.close()

    flash('Cliente eliminado correctamente', 'success')
    return redirect(url_for('clientes'))


# Aquí tus otras rutas (login, logout, clientes, productos, etc.)

@app.route('/productos')
@login_required
def productos():
    conn = get_db_connection()

    search = request.args.get('search', '').strip()
    categoria_id = request.args.get('categoria_id', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # Armado de consulta dinámica
    base_query = '''
        SELECT p.*, c.nombre AS categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE 1=1
    '''
    count_query = 'SELECT COUNT(*) FROM productos p WHERE 1=1'
    params = []
    count_params = []

    if search:
        base_query += ' AND p.nombre LIKE ?'
        count_query += ' AND p.nombre LIKE ?'
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')

    if categoria_id:
        base_query += ' AND p.categoria_id = ?'
        count_query += ' AND p.categoria_id = ?'
        params.append(categoria_id)
        count_params.append(categoria_id)

    base_query += ' ORDER BY p.nombre ASC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])

    productos = conn.execute(base_query, params).fetchall()
    total = conn.execute(count_query, count_params).fetchone()[0]
    categorias = conn.execute('SELECT * FROM categorias').fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template('productos.html',
                           productos=productos,
                           categorias=categorias,
                           search=search,
                           categoria_id=categoria_id,
                           page=page,
                           total_pages=total_pages)


@app.route('/productos/agregar', methods=['POST'])
@login_required
def agregar_producto():
    nombre = request.form['nombre'].strip()
    categoria_id = int(request.form['categoria'])
    try:
        alto = float(request.form['alto'])
        ancho = float(request.form['ancho'])
        profundidad = float(request.form['profundidad'])
        precio = float(request.form['precio'])
    except ValueError:
        flash('Por favor, ingresa valores numéricos válidos para las dimensiones.', 'danger')
        return redirect(url_for('productos'))

    foto = None
    if 'foto' in request.files:
        file = request.files['foto']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            foto = filename

    if not nombre or not categoria_id:
        flash('El nombre y la categoría son obligatorios.', 'danger')
        return redirect(url_for('productos'))

    conn = get_db_connection()
    conn.execute('INSERT INTO productos (nombre, categoria_id, alto, ancho, profundidad, precio, foto) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (nombre, categoria_id, alto, ancho, profundidad, precio, foto))
    conn.commit()
    conn.close()

    flash('Producto agregado correctamente', 'success')
    return redirect(url_for('productos'))

@app.route('/productos/editar/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        categoria_id = int(request.form['categoria'])  # <- ahora es un ID
        alto = float(request.form['alto'])
        ancho = float(request.form['ancho'])
        profundidad = float(request.form['profundidad'])
        precio = float(request.form['precio'])

        cursor.execute('''
            UPDATE productos
            SET nombre = ?, categoria_id = ?, alto = ?, ancho = ?, profundidad = ?, precio = ?
            WHERE id = ?
        ''', (nombre, categoria_id, alto, ancho, profundidad, precio, producto_id))

        conn.commit()
        conn.close()
        flash('Producto actualizado con éxito', 'success')
        return redirect(url_for('productos'))

    # Obtener producto + categorías para mostrar en el formulario
    producto = cursor.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    categorias = cursor.execute('SELECT * FROM categorias').fetchall()
    conn.close()

    return render_template('editar_producto.html', producto=producto, categorias=categorias)

    producto = cursor.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    conn.close()
    return render_template('editar_producto.html', producto=producto)

@app.route('/productos/eliminar/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
    conn.commit()
    conn.close()
    flash('Producto eliminado correctamente', 'success')
    return redirect(url_for('productos'))


from datetime import datetime
import sqlite3

@app.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
    conn = get_db_connection()
    cursor = conn.cursor()

    clientes = cursor.execute('SELECT * FROM clientes').fetchall()
    productos = cursor.execute('SELECT * FROM productos').fetchall()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        producto_id = request.form.get('producto_id')
        cantidad = int(request.form.get('cantidad'))
        total = float(request.form.get('total'))

        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(
            'INSERT INTO ventas (cliente_id, producto_id, cantidad, total, fecha) VALUES (?, ?, ?, ?, ?)',
            (cliente_id, producto_id, cantidad, total, fecha_actual)
        )
        conn.commit()
        flash('Venta registrada exitosamente.', 'success')
        return redirect(url_for('ventas'))

    # Filtros
    filtro_cliente = request.args.get('filtro_cliente', type=int)
    filtro_producto = request.args.get('filtro_producto', type=int)
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    orden = request.args.get('orden', 'fecha_desc')

    query = '''
        SELECT v.id, v.cliente_id, c.nombre AS cliente_nombre,
               v.producto_id, p.nombre AS producto_nombre, p.precio AS producto_precio,
               v.cantidad, v.total, v.fecha
        FROM ventas v
        JOIN clientes c ON v.cliente_id = c.id
        JOIN productos p ON v.producto_id = p.id
    '''
    condiciones = []
    parametros = []

    if filtro_cliente:
        condiciones.append('v.cliente_id = ?')
        parametros.append(filtro_cliente)
    if filtro_producto:
        condiciones.append('v.producto_id = ?')
        parametros.append(filtro_producto)
    if fecha_desde:
        condiciones.append('date(v.fecha) >= date(?)')
        parametros.append(fecha_desde)
    if fecha_hasta:
        condiciones.append('date(v.fecha) <= date(?)')
        parametros.append(fecha_hasta)

    if condiciones:
        query += ' WHERE ' + ' AND '.join(condiciones)

    # Orden
    if orden == 'fecha_asc':
        query += ' ORDER BY v.fecha ASC'
    elif orden == 'cliente_asc':
        query += ' ORDER BY c.nombre ASC'
    elif orden == 'cliente_desc':
        query += ' ORDER BY c.nombre DESC'
    elif orden == 'producto_asc':
        query += ' ORDER BY p.nombre ASC'
    elif orden == 'producto_desc':
        query += ' ORDER BY p.nombre DESC'
    else:
        query += ' ORDER BY v.fecha DESC'

    ventas = cursor.execute(query, parametros).fetchall()
    conn.close()

    ventas_convertidas = []
    for venta in ventas:
        venta_dict = dict(venta)
        venta_dict['fecha'] = datetime.strptime(venta_dict['fecha'], '%Y-%m-%d %H:%M:%S')
        venta_dict['cliente'] = SimpleNamespace(**{
            'id': venta_dict.pop('cliente_id'),
            'nombre': venta_dict.pop('cliente_nombre')
        })
        venta_dict['producto'] = SimpleNamespace(**{
            'id': venta_dict.pop('producto_id'),
            'nombre': venta_dict.pop('producto_nombre'),
            'precio': venta_dict.pop('producto_precio')
        })
        ventas_convertidas.append(SimpleNamespace(**venta_dict))

    return render_template(
        'ventas.html',
        clientes=clientes,
        productos=productos,
        ventas=ventas_convertidas
    )

@app.route('/ventas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_venta(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la venta por id
    venta = cursor.execute('SELECT * FROM ventas WHERE id = ?', (id,)).fetchone()
    if not venta:
        flash('Venta no encontrada.', 'danger')
        return redirect(url_for('ventas'))

    # Obtener clientes y productos para llenar los selects
    clientes = cursor.execute('SELECT * FROM clientes').fetchall()
    productos = cursor.execute('SELECT * FROM productos').fetchall()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        producto_id = request.form.get('producto_id')
        cantidad = int(request.form.get('cantidad'))
        total = float(request.form.get('total'))
        observacion = request.form.get('observacion', '')

        cursor.execute('''
            UPDATE ventas
            SET cliente_id = ?, producto_id = ?, cantidad = ?, total = ?, observacion = ?
            WHERE id = ?
        ''', (cliente_id, producto_id, cantidad, total, observacion, id))
        conn.commit()
        conn.close()

        flash('Venta actualizada correctamente.', 'success')
        return redirect(url_for('ventas'))

    # Preparar datos para la plantilla (convertir Row a dict)
    venta_dict = dict(venta)

    return render_template('editar_venta.html', venta=venta_dict, clientes=clientes, productos=productos)

@app.route('/ventas/eliminar/<int:venta_id>')
@login_required
def eliminar_venta(venta_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))
    conn.commit()
    conn.close()

    flash('Venta eliminada correctamente', 'success')
    return redirect(url_for('ventas'))


@app.route('/proveedores')
@login_required
def proveedores():
    q = request.args.get('q', '').strip()
    conn = get_db_connection()
    
    if q:
        query = """
            SELECT * FROM proveedores
            WHERE nombre LIKE ? OR telefono LIKE ? OR email LIKE ? OR direccion LIKE ?
        """
        like_q = f'%{q}%'
        proveedores = conn.execute(query, (like_q, like_q, like_q, like_q)).fetchall()
    else:
        proveedores = conn.execute('SELECT * FROM proveedores').fetchall()
    
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores, q=q)

@app.route('/proveedores/registrar', methods=['POST'])
def registrar_proveedor():
    nombre = request.form['nombre']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    email = request.form['email']

    conn = get_db_connection()  # ✅ Ahora usás basededatos.db
    cur = conn.cursor()
    cur.execute("INSERT INTO proveedores (nombre, telefono, direccion, email) VALUES (?, ?, ?, ?)",
                (nombre, telefono, direccion, email))
    conn.commit()
    conn.close()

    return redirect(url_for('proveedores'))

@app.route('/proveedores/editar/<int:proveedor_id>', methods=['GET', 'POST'])
@login_required
def editar_proveedor(proveedor_id):
    conn = get_db_connection()
    proveedor = conn.execute('SELECT * FROM proveedores WHERE id = ?', (proveedor_id,)).fetchone()

    if proveedor is None:
        flash('Proveedor no encontrado', 'danger')
        conn.close()
        return redirect(url_for('proveedores'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        telefono = request.form['telefono'].strip()
        email = request.form['email'].strip()
        direccion = request.form['direccion'].strip()

        if not nombre or not telefono:
            flash('El nombre y teléfono son obligatorios.', 'danger')
            return redirect(url_for('editar_proveedor', proveedor_id=proveedor_id))

        conn.execute('UPDATE proveedores SET nombre = ?, telefono = ?, email = ?, direccion = ? WHERE id = ?',
                     (nombre, telefono, email, direccion, proveedor_id))
        conn.commit()
        conn.close()

        flash('Proveedor actualizado correctamente.', 'success')
        return redirect(url_for('proveedores'))

    conn.close()
    return render_template('editar_proveedor.html', proveedor=proveedor)


@app.route('/proveedores/eliminar/<int:proveedor_id>', methods=['POST'])
@login_required
def eliminar_proveedor(proveedor_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM proveedores WHERE id = ?', (proveedor_id,))
    conn.commit()
    conn.close()
    flash('Proveedor eliminado correctamente.', 'success')
    return redirect(url_for('proveedores'))





@app.route('/exportar_clientes_avanzado', methods=['POST'])
@login_required
def exportar_clientes_avanzado():
    data = request.get_json()
    filtro = data.get('filtro', '').lower()
    formato = data.get('formato', 'pdf')

    conn = get_db_connection()
    clientes = conn.execute('SELECT * FROM clientes').fetchall()
    conn.close()

    if filtro:
        clientes = [c for c in clientes if
                    filtro in c['nombre'].lower() or
                    filtro in c['telefono'].lower() or
                    filtro in c['email'].lower() or
                    filtro in c['localidad'].lower()]

    buffer = io.BytesIO()

    if formato == 'pdf':
        pdf = SimpleDocTemplate(buffer, pagesize=letter)
        elementos = []

        data_table = [['ID', 'Nombre', 'Teléfono', 'Localidad', 'Email']]
        for c in clientes:
            data_table.append([c['id'], c['nombre'], c['telefono'], c['localidad'], c['email']])

        tabla = Table(data_table, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elementos.append(tabla)
        pdf.build(elementos)
        buffer.seek(0)

        response = make_response(buffer.read())
        response.headers['Content-Disposition'] = 'attachment; filename=clientes.pdf'
        response.headers['Content-Type'] = 'application/pdf'
        return response

    else:
        return jsonify({'error': 'Formato no soportado'}), 400
    

def obtener_ventas_mensuales():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%m', fecha) as mes, COUNT(*) as total
        FROM ventas
        GROUP BY mes
    """)
    datos = cursor.fetchall()
    conn.close()
    ventas_por_mes = {mes: 0 for mes in ['01','02','03','04','05','06','07','08','09','10','11','12']}
    for fila in datos:
        ventas_por_mes[fila['mes']] = fila['total']
    return [ventas_por_mes[mes] for mes in ['01','02','03','04','05','06']]

def obtener_clientes_mensuales():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%m', fecha_registro) as mes, COUNT(*) as total
        FROM clientes
        GROUP BY mes
    """)
    datos = cursor.fetchall()
    conn.close()
    clientes_por_mes = {mes: 0 for mes in ['01','02','03','04','05','06','07','08','09','10','11','12']}
    for fila in datos:
        clientes_por_mes[fila['mes']] = fila['total']
    return [clientes_por_mes[mes] for mes in ['01','02','03','04','05','06']]

def obtener_productos_mas_vendidos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nombre, SUM(v.cantidad) as total_vendido
        FROM ventas v
        JOIN productos p ON p.id = v.producto_id
        GROUP BY p.nombre
        ORDER BY total_vendido DESC
        LIMIT 4
    """)
    datos = cursor.fetchall()
    conn.close()
    labels = [fila['nombre'] for fila in datos]
    cantidades = [fila['total_vendido'] for fila in datos]
    return labels, cantidades


@app.route('/api/informe_mensual')
@login_required
def informe_mensual():
    ventas = obtener_ventas_mensuales()
    clientes = obtener_clientes_mensuales()
    productos_labels, productos_data = obtener_productos_mas_vendidos()

    return jsonify({
        'ventas_mensuales': ventas,
        'clientes_mensuales': clientes,
        'productos_labels': productos_labels,
        'productos_data': productos_data
    })

@app.route('/perfil')
@login_required
def perfil():
    # Aquí ponés la lógica para mostrar la página de perfil
    return render_template('perfil.html')

with sqlite3.connect('basededatos.db') as conn:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT NOT NULL,
        email TEXT,
        direccion TEXT
    )
    """)
    conn.commit()

if __name__ == '__main__':
    app.run(debug=True)