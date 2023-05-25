from flask import Flask, render_template, request, redirect, session, send_file, send_from_directory
from config import Config
import builtins as print
from werkzeug.utils import secure_filename
from datetime import datetime
import pymysql
import os
import pandas as pd
import numpy as np
import re
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg')

app = Flask(__name__)
app.secret_key = 'mysecretkey'
app.config.from_object('config.Config')

@app.route('/')
def index():
    user_id = session.get('user_id')
    is_admin = session.get('is_admin')
    conn = Config.get_db()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute('SELECT C.id, U.username, CT.name, filename AS pdf_path, upload_date FROM certificates C INNER JOIN users U ON C.user_id = U.id INNER JOIN certificate_types CT ON C.type_id = CT.id ORDER BY upload_date')
    else:
        cursor.execute('SELECT C.id, U.username, CT.name, filename AS pdf_path, upload_date FROM certificates C INNER JOIN users U ON C.user_id = U.id INNER JOIN certificate_types CT ON C.type_id = CT.id WHERE C.user_id = %s ORDER BY upload_date', (user_id,))
    certificates = cursor.fetchall()
    cursor.close()
    conn.close()
    es_admin = session.get('is_admin', False)
    return render_template('index.html', certificates=certificates, es_admin=es_admin)


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            # Si las credenciales son válidas, redirige al usuario a la página de inicio
            return redirect('/')
        else:
            # Si las credenciales son inválidas, muestra un mensaje de error
            error = 'Nombre de usuario o contraseña incorrectos'
            return render_template('login.html', error=error)
    else:
        # Si la solicitud es GET, muestra la página de inicio de sesión
        return render_template('login.html')

def authenticate(username, password):
    conn = Config.get_db()
    cursor = conn.cursor()
    query = f"SELECT * FROM Users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    if row is not None:
        session['user_id'] = row[0]
        session['is_admin'] = row[3]
        return True
    else:
        return False
   
# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    return redirect('/gracias')

@app.route('/gracias')
def gracias():
    return render_template('gracias.html')

# Insert Users - User_details
class User:
    def __init__(self, username, password, is_admin):
        self.username = username
        self.password = password
        self.is_admin = is_admin

class UserDetails:
    def __init__(self, user_id, name, last_name, document, email, status):
        self.user_id = user_id
        self.name = name
        self.last_name = last_name
        self.document = document
        self.email = email
        self.status = status

@app.route('/nuevo_usuario', methods=['GET', 'POST'])
def agregar_usuario():
    if request.method == 'POST':
        # Obtener los datos del formulario
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        last_name = request.form['last_name']
        document = request.form['document']
        email = request.form['email']
        status = request.form['status']
        is_admin = request.form['is_admin']
        is_admin = True if is_admin == '1' else False

        # Agregar el usuario a la tabla users
        user = User(username=username, password=password, is_admin=is_admin)
        conn = Config.get_db()
        cursor = conn.cursor()
        query = "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)"
        cursor.execute(query, (user.username, user.password, user.is_admin))
        user_id = cursor.lastrowid
        conn.commit()

        # Agregar los detalles del usuario a la tabla user_details
        user_details = UserDetails(user_id=user_id, name=name, last_name=last_name, document=document, email=email, status=status)
        query = "INSERT INTO user_details (user_id, name, last_name, document, email, status) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (user_details.user_id, user_details.name, user_details.last_name, user_details.document, user_details.email, user_details.status))
        conn.commit()

        conn.close()

        return redirect('/lista_usuarios')
    else:
        return render_template('nuevo_usuario.html')

    
# Listar usuarios
@app.route('/lista_usuarios')
def lista_usuarios():
    conn = Config.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT u.username, u.password, u.is_admin, ud.name, ud.last_name, ud.document, ud.email, ud.status FROM users u INNER JOIN user_details ud ON u.id = ud.user_id")

    usuarios = []
    for row in cursor.fetchall():
        usuario = {'username': row[0], 'password': row[1], 'is_admin': row[2], 'name': row[3], 'last_name': row[4], 'document': row[5], 'email': row[6], 'status': row[7], 'ruta': f"/usuario/{row[0]}"}
        usuarios.append(usuario)

    conn.close()

    return render_template('lista_usuarios.html', usuarios=usuarios)

# Subir certificado
@app.route('/subir_certificado', methods=['GET'])
def subir_certificado_form():
    conn = Config.get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, document FROM user_details')
    users = cursor.fetchall()
    cursor.execute('SELECT id, name FROM certificate_types')
    certificate_types = cursor.fetchall()
    conn.close()
    return render_template('subir_certificado.html', users=users, certificate_types=certificate_types)


@app.route('/subir_certificado', methods=['POST']) 
def subir_certificado():
    
    conn = Config.get_db() 
    cursor = conn.cursor()      
         
    try:
    
        user_id = request.form['user_id']   
        type_id = request.form['type_id']
        file = request.files['file']
        filename = secure_filename(file.filename)
        upload_date = datetime.now()          
            
        # Inserta registro con solo el filename original  
        cursor.execute("""
            INSERT INTO certificates(user_id, type_id, filename, upload_date)  
            VALUES (%s, %s, %s, %s)
        """, (user_id, type_id, filename, upload_date))  
            
        # Obtiene el certificate_id generado        
        certificate_id = cursor.lastrowid  
                
        # Actualiza el registro usando solo el ID          
        cursor.execute("""
            UPDATE certificates   
            SET filename = %s
            WHERE id = %s  
        """, (f"{certificate_id}.pdf", certificate_id))  
            
        conn.commit()
        
    except Exception as e:      
          print(e)  
            
    finally:  
        conn.close()  
                
    # Guarda el archivo usando solo el ID  
    file.save('C:/certificados/static/' + f"{certificate_id}.pdf")
                
    return redirect('/')

# Carga masiva
@app.route('/carga_masiva_certificados', methods=['POST'])
def carga_masiva_certificados():
    file = request.files['file']  # Obtener el archivo cargado
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file, dtype={'filename': str})  # Leer el archivo como un DataFrame de Pandas

        conn = Config.get_db()
        cursor = conn.cursor()

        # Iterar sobre cada fila del DataFrame y agregar los certificados a la base de datos
        for index, row in df.iterrows():
            user_id = int(np.int64(row['user_id']))  
            type_id = int(np.int64(row['type_id']))
            filename = row['filename']
            upload_date = datetime.strptime(row['upload_date'], '%Y-%m-%d')
            query = 'INSERT INTO certificates (user_id, type_id, filename, upload_date) VALUES (%s, %s, %s, %s)'
            cursor.execute(query, (user_id, type_id, filename, upload_date))

        conn.commit()
        conn.close()

        # Notificar al usuario que la carga masiva de certificados se ha completado
        return "La carga masiva de certificados se ha completado"
    else:
        # Notificar al usuario que el formato del archivo no es válido
        return "El formato del archivo no es válido. Solo se permiten archivos CSV."
    
# Ruta upload
@app.route('/upload') 
def upload_form():
    return render_template('carga_masiva_certificados.html')

# Ruta estatica
@app.route('/static/<path:filename>')
def static_file(filename):
    return send_file('static/' + filename)

# Graficos
def generate_upload_count_graph():
    conn = Config.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DATE(upload_date) AS upload_date,  
               COUNT(*) as count
        FROM certificates
        GROUP BY DATE(upload_date)
    """)
    results = cursor.fetchall()

    dates = [result[0] for result in results]
    counts = [result[1] for result in results]

    plt.bar(dates, counts)
    plt.xticks(dates, rotation=90)
    plt.xlabel("Date")
    plt.ylabel("Count")

    plt.savefig('static/upload_count.png')
    plt.clf()  # Limpiar figura

    cursor.close()
    conn.close()

def generate_download_count_graph():
    conn = Config.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DATE(download_date) AS download_date,  
               COUNT(*) as count 
        FROM certificate_downloads
        GROUP BY DATE(download_date)
    """)
    results = cursor.fetchall()

    dates = [result[0] for result in results]
    counts = [result[1] for result in results]

    plt.bar(dates, counts)
    plt.xticks(dates, rotation=90)

    plt.savefig('static/download_count.png')
    plt.clf()  # Limpiar figura

    cursor.close()
    conn.close() 

# Dashboard
@app.route('/dashboard')
def dashboard():
    
    generate_upload_count_graph()
    generate_download_count_graph()
    
    return render_template('dashboard.html')

# Obtener datos de certificados
def get_certificate_details(filename):
    conn = Config.get_db()
    cursor = conn.cursor()     
    cursor.execute("""
        SELECT * FROM certificates 
        WHERE filename = %s  
    """, (filename,))     
    certificate_row = cursor.fetchone()
    
    # Obtener datos del certificado y user/certificate ids      
    certificate = {}     
    for i, column_name in enumerate(cursor.description):
        certificate[column_name[0]] = certificate_row[i]
        
    user_id = certificate['user_id']  
    certificate_id = certificate['id']   
      
    conn.close()
      
    return certificate, user_id, certificate_id

@app.route('/descargas/<certificate_id>.pdf')
def download(certificate_id):
    try:
        conn = Config.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM certificates WHERE id = %s", (certificate_id,))
        result = cursor.fetchone() 
        user_id = result[0]

        download_date = datetime.now()

        cursor.execute("INSERT INTO certificate_downloads (certificate_id, user_id, download_date) VALUES (%s, %s, %s)", (certificate_id, user_id, download_date))
        conn.commit()
        return send_from_directory("static", f"{certificate_id}.pdf", as_attachment=True)
    except Exception as e:
        print(e)
        return "Error al descargar el certificado"

#download("certificado.pdf", 1)

# Ruta formulario carga csv
@app.route("/certificate_form")
def certificate_form():
    return render_template("certificate_form.html")

if __name__ == '__main__':
    app.run(debug=True)