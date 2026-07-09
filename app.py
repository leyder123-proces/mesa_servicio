from flask import Flask, request, render_template, render_template_string
import os
import random
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# En Render, la carpeta '/tmp' garantiza permisos de escritura estables
UPLOAD_FOLDER = '/tmp/evidencias'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Archivo de texto para almacenar la base de datos de los tickets
TICKETS_FILE = '/tmp/tickets.txt'

# CONFIGURACIÓN DEL CORREO EMISOR
CORREO_EMISOR = "msprocesosconfiamoscol@gmail.com"
CORREO_PASSWORD = "ahfq beyj boky zlhz" 

def enviar_correo_ticket(correo_destino, ticket_id, usuario, requerimiento):
    mensaje = MIMEMultipart()
    mensaje['From'] = CORREO_EMISOR
    mensaje['To'] = correo_destino
    mensaje['Subject'] = f"🔔 Confirmación de Ticket: {ticket_id}"
    
    cuerpo = f"""
    Hola {usuario},
    
    Hemos registrado exitosamente tu requerimiento en la Mesa de Servicio.
    
    DETALLES DE TU REPORTE:
    ----------------------------------------
    ID TICKET: {ticket_id}
    REQUERIMIENTO: {requerimiento}
    ----------------------------------------
    
    Estaremos trabajando en tu solicitud lo antes posible.
    
    Atentamente,
    Mesa de Servicios - Procesos Confiamos
    """
    mensaje.attach(MIMEText(cuerpo, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(CORREO_EMISOR, CORREO_PASSWORD)
        server.sendmail(CORREO_EMISOR, correo_destino, mensaje.as_string())
        server.quit()
        print(f"--> ¡Correo enviado con éxito a {correo_destino}!")
    except Exception as e:
        print(f"--> ERROR AL ENVIAR CORREO: {e}")

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/crear-ticket', methods=['POST'])
def crear_ticket():
    nombre = request.form['nombre']
    correo_usuario = request.form['correo_usuario'] 
    requerimiento = request.form['requerimiento']
    evidencia = request.files.get('evidencia')
    
    # 1. Guardar archivo adjunto de forma limpia y segura
    nombre_archivo = "Sin evidencia"
    if evidencia and evidencia.filename != '':
        nombre_archivo = evidencia.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
        evidencia.save(filepath)
    
    # 2. Generar ID único del Ticket
    ahora = datetime.now()
    fecha_ticket = ahora.strftime("%Y%m%d")
    fecha_legible = ahora.strftime("%Y-%m-%d %H:%M:%S")
    numero_aleatorio = random.randint(100, 999)
    ticket_id = f"TK-{fecha_ticket}-{numero_aleatorio}"
    
    # 3. Guardar en el archivo de texto en la ruta /tmp
    with open(TICKETS_FILE, "a", encoding="utf-8") as archivo:
        archivo.write(f"========================================\n")
        archivo.write(f"TICKET: {ticket_id}\n")
        archivo.write(f"FECHA: {fecha_legible}\n")
        archivo.write(f"USUARIO: {nombre}\n")
        archivo.write(f"CORREO: {correo_usuario}\n")
        archivo.write(f"REQUERIMIENTO: {requerimiento}\n")
        archivo.write(f"ARCHIVO ADJUNTO: {nombre_archivo}\n")
        archivo.write(f"========================================\n\n")
    
    # 4. Enviar notificación por correo electrónico
    enviar_correo_ticket(correo_usuario, ticket_id, nombre, requerimiento)
    
    # Interfaz de éxito
    pantalla_exito = f"""
    <div style="font-family:Arial, sans-serif; text-align:center; margin-top:80px;">
        <div style="max-width:450px; margin:auto; background:#fff; padding:30px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1); border-top: 5px solid #28a745;">
            <h2 style="color:#28a745; margin-bottom:10px;">¡Ticket Generado Exitosamente!</h2>
            <p style="color:#555;">Hola <b>{nombre}</b>, hemos registrado tu requerimiento.</p>
            <p style="color:#777; font-size:14px;">Se ha enviado una copia y confirmación al correo: <b>{correo_usuario}</b></p>
            <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
            <p style="font-size:14px; color:#777; margin-bottom:5px;">TU NÚMERO DE TICKET ES:</p>
            <div style="background:#e8f5e9; color:#2e7d32; display:inline-block; padding:15px 30px; border-radius:6px; font-size:24px; font-weight:bold; letter-spacing:1px;">
                {ticket_id}
            </div>
            <br><br>
            <a href="/" style="color:#007bff; text-decoration:none; font-size:14px;">← Reportar otro requerimiento</a>
        </div>
    </div>
    """
    return render_template_string(pantalla_exito)

# RUTA SECRETA PARA VER TUS RESULTADOS DESDE EL NAVEGADOR
@app.route('/ver-base-datos-procesos')
def ver_tickets():
    if not os.path.exists(TICKETS_FILE):
        return "<h3>Aún no se han registrado tickets en el sistema.</h3>"
    with open(TICKETS_FILE, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()
    return f"<pre style='padding:20px; background:#222; color:#fff; font-family:monospace;'>{contenido}</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
