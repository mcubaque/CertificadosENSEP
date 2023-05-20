from flask import Flask, render_template, request, redirect, session, send_file, send_from_directory
from config import get_db
from config import Config
import pyodbc
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg')
from xlrd import open_workbook
import pdfkit
import io
import csv
from fpdf import FPDF
from docx import Document 
from docx2pdf import convert


app = Flask(__name__)
app.secret_key = 'mysecretkey'
app.config.from_object('config.Config')



@app.route('/')
def index():
    user_id = session.get('user_id')
    is_admin = session.get('is_admin')
    conn = get_db()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute('SELECT C.id, U.username, CT.name, filename AS pdf_path, upload_date FROM certificates C INNER JOIN users U ON C.user_id = U.id INNER JOIN certificate_types CT ON C.type_id = CT.id')
    else:
        cursor.execute('SELECT C.id, U.username, CT.name, filename AS pdf_path, upload_date FROM certificates C INNER JOIN users U ON C.user_id = U.id INNER JOIN certificate_types CT ON C.type_id = CT.id WHERE C.user_id = ?', (user_id,))
    certificates = cursor.fetchall()
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
    conn_str = f"DRIVER={Config.SQL_DRIVER};SERVER={Config.SQL_SERVER};DATABASE={Config.SQL_DATABASE};UID={Config.SQL_USERNAME};PWD={Config.SQL_PASSWORD}"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    query = f"SELECT * FROM Users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    if row is not None:
        session['user_id'] = row[0]
        session['is_admin'] = row[3]  # Asigna el valor de is_admin a la variable de sesión
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

        # Agregar el usuario a la tabla users
        user = User(username=username, password=password, is_admin=is_admin)
        conn = get_db()
        cursor = conn.cursor()
        query = f"INSERT INTO users (username, password, is_admin) OUTPUT INSERTED.id VALUES ('{user.username}', '{user.password}', '{user.is_admin}')"
        cursor.execute(query)
        user_id = cursor.fetchone()[0]  # Obtener el primer valor de la primera fila
        conn.commit()

        # Agregar los detalles del usuario a la tabla user_details
        user_details = UserDetails(user_id=user_id, name=name, last_name=last_name, document=document, email=email, status=status)
        query = f"INSERT INTO user_details (user_id, name, last_name, document, email, status) VALUES ({user_details.user_id}, '{user_details.name}', '{user_details.last_name}', '{user_details.document}', '{user_details.email}', '{user_details.status}')"
        cursor.execute(query)
        conn.commit()

        conn.close()

        return redirect('/lista_usuarios')
    else:
        return render_template('nuevo_usuario.html')
    
# Listar usuarios
@app.route('/lista_usuarios')
def lista_usuarios():
    conn = get_db()
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, document FROM user_details')
    users = cursor.fetchall()
    cursor.execute('SELECT id, name FROM certificate_types')
    certificate_types = cursor.fetchall()
    conn.close()
    return render_template('subir_certificado.html', users=users, certificate_types=certificate_types)


@app.route('/subir_certificado', methods=['POST'])
def subir_certificado():
    user_id = request.form['user_id']
    type_id = request.form['type_id']
    file = request.files['file']
    filename = secure_filename(file.filename)
    upload_date = datetime.now()
    conn = get_db()
    cursor = conn.cursor()
    query = 'INSERT INTO certificates (user_id, type_id, filename, upload_date) VALUES (?, ?, ?, ?)'
    cursor.execute(query, (user_id, type_id, filename, upload_date))
    print(user_id, type_id, filename, upload_date)
    conn.commit()
    file.save('C:/certificados/static/' + filename)
    conn.close()
    return redirect('/')

# Carga masiva
@app.route('/carga_masiva_certificados', methods=['POST'])
def carga_masiva_certificados():
    file = request.files['file']  # Obtener el archivo cargado
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file, dtype={'filename': str})  # Leer el archivo como un DataFrame de Pandas

        conn = get_db()
        cursor = conn.cursor()

        # Iterar sobre cada fila del DataFrame y agregar los certificados a la base de datos
        for index, row in df.iterrows():
            user_id = int(np.int64(row['user_id']))  
            type_id = int(np.int64(row['type_id']))
            filename = row['filename']
            upload_date = datetime.strptime(row['upload_date'], '%Y-%m-%d')
            query = 'INSERT INTO certificates (user_id, type_id, filename, upload_date) VALUES (?, ?, ?, ?)'
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
    
    conn = get_db()  
    cursor = conn.cursor()
        
    cursor.execute("""
        SELECT CONVERT(date, upload_date) AS upload_date,  
               COUNT(*) as count
        FROM certificates   
        GROUP BY CONVERT(date, upload_date)    
    """)     
    results = cursor.fetchall()  
        
    plt.bar([result[0] for result in results],  
             [result[1] for result in results])
    plt.xticks([result[0] for result in results], rotation=90)
    plt.xlabel("Date") 
    plt.ylabel("Count")       
    
    plt.savefig('static/upload_count.png')  
    plt.clf() # Limpiar figura 
def generate_download_count_graph(): 
          
    conn = get_db()  
    cursor = conn.cursor() 
        
    cursor.execute("""
       SELECT CONVERT(date, download_date) AS download_date,  
              COUNT(*) as count 
       FROM certificate_downloads   
       GROUP BY CONVERT(date, download_date)        
    """)
    results = cursor.fetchall()
        
    plt.bar([result[0] for result in results],
            [result[1] for result in results])
    plt.xticks([result[0] for result in results], rotation=90)
        
    plt.savefig('static/download_count.png')
    plt.clf() # Limpiar figura 

# Dashboard
@app.route('/dashboard')
def dashboard():
    
    generate_upload_count_graph()
    generate_download_count_graph()
    
    return render_template('dashboard.html')

# Downloads - Historico. Alimenta certificate_downloads
# @app.route('/download/<int:certificate_id>/<path:filepath>/<string:filename>')
# def download(certificate_id, filepath, filename):
#     user_id = session['user_id']  
    
#     conn = get_db()
#     cursor = conn.cursor()

#     cursor.execute("INSERT INTO certificate_downloads (certificate_id, user_id, download_date) VALUES (?, ?, ?)",  
#                 (certificate_id, user_id, datetime.now()) )
#     conn.commit()
#     conn.close()

    # Aquí puedes utilizar send_from_directory() para descargar el archivo
    #return 'Descarga exitosa'


# Obtener datos de certificados
def get_certificate_by_filename(filename):
    conn = get_db()
    cursor = conn.cursor()     
    cursor.execute("""
        SELECT * FROM certificates 
        WHERE filename = ?  
    """, (filename,))     
    certificate_row = cursor.fetchone()
    if certificate_row is None:
        return None
    certificate = {}
    for i, column_name in enumerate(cursor.description):
        certificate[column_name[0]] = certificate_row[i]
    return certificate

# Descargar un certificado y registrar la descarga en la base de datos
def get_user_id(certificate_id, cursor):
    cursor.execute("SELECT user_id FROM certificates WHERE id = ?", (certificate_id,))
    user_id = cursor.fetchone()[0]       
    return user_id

@app.route('/download/<filename>/<certificate_id>')
def download(filename, certificate_id):
    conn = get_db()  
    cursor = conn.cursor()
    
    file_path = os.path.join('static', filename)
          
    try:   
        user_id = get_user_id(certificate_id, cursor)
              
        cursor.execute("""
           INSERT INTO certificate_downloads   
           VALUES (?, ?, ?)    
        """, (certificate_id, user_id, datetime.now())) 
              
        conn.commit()
                
            
    finally:
        conn.close()
            
    return send_file(file_path, as_attachment=True)

# Ruta formulario carga csv
@app.route("/certificate_form")
def certificate_form():
    return render_template("certificate_form.html")

# Generar Certificados
# @app.route("/certificate", methods=["POST", "GET"])
# def generate_certificate():

    
#     if request.method == "POST":
#         csv_file = request.files.get("csv_file")
#         name = "No name"
#         course = "No course"
#         date = "No date"

#         if csv_file:
#             with io.TextIOWrapper(csv_file, encoding='utf-8') as csv_data:
#                 csv_reader = csv.reader(csv_data)
#                 data = []

#                 for row in csv_reader:
#                     data.append(row)

#             for row in data:
#                 try:
#                     name = row[0]
#                     course = row[1]
#                     date = row[2]
#                 except IndexError:
#                     print("Invalid row, skipping")

#                 # Abrir plantilla
#                 document = Document('static/diploma.docx')

#                 # Actualizar texto
#                 for paragraph in document.paragraphs:
#                     for run in paragraph.runs:
#                         if '{name}' in run.text:
#                             run.text = run.text.replace('{name}', name)

#                         if '{course}' in run.text:
#                             run.text = run.text.replace('{course}', course)

#                         if '{date}' in run.text:
#                             run.text = run.text.replace('{date}', date)

#                 # Guardar como PDF
#                 # Eliminar archivo previo si existe
#                 name_path = f"static/name.pdf"
#                 if os.path.exists(name_path):
#                     os.remove(name_path)

#                 pdf_path = f"static/{name}.pdf"
#                 if os.path.exists(pdf_path):
#                     os.remove(pdf_path)

#                 temp_docx_path = f"static/temp.docx"
#                 if os.path.exists(temp_docx_path):
#                     os.remove(temp_docx_path)
#                 document.save(temp_docx_path)
#                 convert(temp_docx_path, pdf_path)

#             return send_from_directory("static", f"{name}.pdf")

#     return render_template("certificate_form.html")

if __name__ == '__main__':
    app.run(debug=True)