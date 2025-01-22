import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import folium
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'super'

db_config = {
    'host': '192.168.20.5',
    'user': 'remote',
    'password': 'Intercom.2025',
    'database': 'coordenadas'
}

app.permanent_session_lifetime = timedelta(minutes=30)

@app.route('/inicio', methods=['GET', 'POST'])
def inicio():
    if request.method == 'POST':
        correo = request.form['correo']
        clave = request.form['clave']
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            query = "SELECT id, clave FROM usuarios WHERE correo = %s"
            cursor.execute(query, (correo,))
            data = cursor.fetchone()
            cursor.close()
            conn.close()
            if data and data[1] == clave:
                session.permanent = True
                session['usuario'] = 'usuario'  # Guardar el ID del usuario
                flash("Inicio de sesión exitoso.")
                return redirect(url_for('agregar'))  # Redirigir a /agregar
            else:
                flash("Usuario o contraseña incorrectos.")  # Flash para el error
        except mysql.connector.Error as err:
            mensaje = f"Error de conexión o ejecución: {err}"
            flash(mensaje)  # Flash para el error
        return render_template('inicioSesion.html')
    elif request.method == 'GET':
        return render_template('inicioSesion.html')

@app.route('/cerrar', methods=['GET', 'POST'])
def cerrar():
    session.pop('usuario', None)
    flash("Sesión cerrada.")
    return redirect(url_for("inicio"))

@app.before_request
def check_session_timeout():
    if 'usuario' in session:
        session.modified = True
    else:
        if request.endpoint != 'inicio' and request.endpoint != 'static':
            return redirect(url_for('inicio'))

def revisaSesion():
    if 'usuario' in session:
        return True
    else:
        return False
        

@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if revisaSesion:
        if request.method == 'POST':
            lat = request.form['latitud']
            lon = request.form['longitud']
            nombre = request.form['nombreCaja']
            cantidad = request.form['numero']
            planta = request.form['planta']
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                query = "INSERT INTO coordenadas (latitud, longitud, nombreCaja, cantidadClientes, planta) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (lat, lon, nombre, cantidad, planta))
                conn.commit()
                cursor.close()
                conn.close()
                mensaje = "Ubicacion agregada con éxito."
                flash(mensaje)
            except mysql.connector.Error as err:
                mensaje = f"Error de conexión o ejecución: {err}"
                flash(mensaje)
                return render_template('agregarCoordenadas.html', actualizar=False)

        return render_template('agregarCoordenadas.html', actualizar=False)
    else:
        mensaje = "Por favor, inicie sesión primero."
        flash(mensaje)
        return redirect(url_for('inicio'))


@app.route('/actualizar', methods=['POST'])
def actualizar():
    if not revisaSesion():
        mensaje = "Por favor, inicie sesión primero."
        flash(mensaje)
        return redirect(url_for('inicio'))
    else:
        if request.method == 'POST':
            dispositivo_id = request.form['id']
        
            # Conexión a la base de datos
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Consulta SQL para obtener los datos del dispositivo por id
            cursor.execute("SELECT * FROM coordenadas WHERE id = %s", (dispositivo_id,))
            dispositivo = cursor.fetchone()
            cursor.close()
            conn.close()

            if dispositivo:
                # Si encontramos el dispositivo, rellenamos el formulario con los datos
                id, latitud, longitud, nombreCaja, cantidadClientes, planta, foto = dispositivo
                flash("Dispositivo encontrado con exito")
                return render_template('actualizarCoordenadas.html', id=id, nombreCaja=nombreCaja, planta=planta, 
                                   cantidadClientes=cantidadClientes, latitud=latitud, longitud=longitud)
            else:
            # Si no encontramos el dispositivo, mostramos el mapa
                flash("No se encontró el dispositivo con el id proporcionado.")
                return redirect(url_for('mapa'))
            
@app.route('/actualizarInfo', methods=['POST'])
def actualizarInfo():
    if not revisaSesion:
        mensaje = "Por favor, inicie sesión primero."
        flash(mensaje)
        return redirect(url_for('inicio'))
    else:
        if request.method == 'POST':
            id = request.form['id']
            nombre = request.form['nombreCaja']
            cantidad = request.form['cantidadClientes']
            planta = request.form['planta']
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                query = "UPDATE coordenadas SET nombreCaja=%s, cantidadClientes=%s, planta=%s WHERE id=%s"
                cursor.execute(query, (nombre, cantidad, planta, id))
                conn.commit()
                mensaje = "Dispositivo actualizado con exito"
                flash(mensaje)
                return redirect(url_for('mapa'))
            except mysql.connector.Error as err:
                mensaje = f"Error de conexión o ejecución: {err}"
                flash(mensaje)
    
@app.route('/mapa', methods=['GET', 'POST'])
def mapa():
    if not revisaSesion():
        flash("Por favor, inicie sesión primero.")
        return redirect(url_for('inicio'))
    else:
        #Obtener las coordenadas
        query = "SELECT id, latitud, longitud, nombreCaja, cantidadClientes, planta, foto FROM coordenadas WHERE 1"
        params = []
        numero_minimo = 1
        numero_maximo = 8
        plantaF = ''
        nombre = ''
        if request.method == 'POST':
            plantaF = request.form.get('exampleFormControlInput4', '')
            numero_minimo = int(request.form.get('numeroMinimo', 1))  # Convertimos a entero
            numero_maximo = int(request.form.get('numeroMaximo', 8))  # Convertimos a entero
            nombre = request.form.get('exampleFormControlInput1', '')
            #Filtro por planta
            if plantaF:
                query += " AND planta = %s"
                params.append(plantaF)
            #Filtro por cantidad de clientes
            query += " AND cantidadClientes BETWEEN %s AND %s"
            params.append(numero_minimo)
            params.append(numero_maximo)
            #Filtro por nombre de caja
            if nombre:
                query += " AND nombreCaja = %s"
                params.append(nombre)
        try:
            conn= mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            if params:  # Si no se han añadido filtros
                cursor.execute(query, tuple(params))
            else:
                cursor.execute(query)
            data = cursor.fetchall()
            mapa = folium.Map(location=[-35.440883, -71.694554], zoom_start=10)
            for id, latitud, longitud, nombreCaja, cantidadClientes, planta, foto in data:
                if latitud is not None and longitud is not None:
                    popupHtml = f"""
                    <div style="text-align:center;">
                    <h4>Id: {id}</h4>
                    <h6>{nombreCaja}</h6>
                    <h6>Clientes: {cantidadClientes}</h6>
                    <h6>{planta}</h6>
                    </div>
                    """
                    popup = folium.Popup(popupHtml, max_width=300)
                    if cantidadClientes == 8:
                        folium.Marker([latitud, longitud], popup=popup, icon=folium.Icon(color='darkred')).add_to(mapa)
                    elif cantidadClientes == 7:
                        folium.Marker([latitud, longitud], popup=popup, icon=folium.Icon(color='lightred')).add_to(mapa)
                    elif cantidadClientes > 4: # 5, 6
                        folium.Marker([latitud, longitud], popup=popup, icon=folium.Icon(color='orange')).add_to(mapa)
                    elif cantidadClientes > 2: # 3, 4
                        folium.Marker([latitud, longitud], popup=popup, icon=folium.Icon(color='lightgreen')).add_to(mapa)
                    else: # 1, 2
                        folium.Marker([latitud, longitud], popup=popup, icon=folium.Icon(color='darkgreen')).add_to(mapa)
            # Obtener opciones para filtros
            cursor.execute("SELECT DISTINCT planta FROM coordenadas")
            opcionesPlanta = cursor.fetchall()
            cursor.execute("SELECT DISTINCT nombreCaja FROM coordenadas")
            opcionesNombre = cursor.fetchall()
            # Generar el HTML del mapa
            mapaHtml = mapa._repr_html_()
            # Renderizar la plantilla con el mapa y opciones
            return render_template('verMapa.html', mapaHtml=mapaHtml, opcionesPlanta=opcionesPlanta,
                                   opcionesNombre=opcionesNombre, plantaSeleccionada=plantaF, 
                                   numeroMinimoSeleccionado=numero_minimo, numeroMaximoSeleccionado=numero_maximo,
                                   nombreSeleccionado=nombre)
        except mysql.connector.Error as err:
            flash(f"Error al realizar la consulta: {err}")
            return render_template('verMapa.html')
    
@app.route('/')
def raiz():
    # Redirige a la URL /inicio
    return redirect(url_for('inicio'))

def archivoPermitido(nombre):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in allowed_extensions

if __name__ == '__main__':
    #app.run(host='10.78.0.64', port=5000, ssl_context='adhoc')
    app.run(host='127.0.0.1', port=5000)
