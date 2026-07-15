from flask import Flask, request, render_template, render_template_string
import os
import random
from datetime import datetime
import smtplib
import ssl
import threading  # <-- IMPORTANTE: Para enviar correos en segundo plano sin congelar la web
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

UPLOAD_FOLDER = '/tmp/evidencias'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TICKETS_FILE = '/tmp/tickets.txt'

CORREO_EMISOR = "msprocesosconfiamoscol@gmail.com"
CORREO_PASSWORD = "ahfq beyj boky zlhz" 

def proceso_envio_correo(correo_destino, ticket_id, usuario, requerimiento):
    """Esta función corre de forma independiente. Si falla, la web no se cae."""
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
    
    Atentamente,
    Mesa de Servicios - Procesos Confiamos
    """
    mensaje.attach(MIMEText(cuerpo, 'plain'))
    
    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto) as server:
            server.login(CORREO_EMISOR, CORREO_PASSWORD)
            server.sendmail(CORREO_EMISOR, correo_destino, mensaje.as_string())
        print(f"--> [OK] Correo enviado a {correo_destino}")
    except Exception as e:
        print(f"--> [ALERTA] No se pudo enviar el correo, pero el ticket ya fue guardado. Error: {e}")

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/crear-ticket', methods=['POST'])
def crear_ticket():
    try:
        nombre = request.form['nombre']
        correo_usuario = request.form['correo_usuario'] 
        requerimiento = request.form['requerimiento']
        evidencia = request.files.get('evidencia')
        
        # 1. Guardar archivo adjunto
        nombre_archivo = "Sin evidencia"
        if evidencia and evidencia.filename != '':
            nombre_archivo = evidencia.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
            evidencia.save(filepath)
        
        # 2. Generar ID único
        ahora = datetime.now()
        fecha_ticket = ahora.strftime("%Y%m%d")
        fecha_legible = ahora.strftime("%Y-%m-%d %H:%M:%S")
        numero_aleatorio = random.randint(100, 999)
        ticket_id = f"TK-{fecha_ticket}-{numero_aleatorio}"
        
        # 3. Guardar en base de datos local
        with open(TICKETS_FILE, "a", encoding="utf-8") as archivo:
            archivo.write(f"========================================\n")
            archivo.write(f"TICKET: {ticket_id}\n")
            archivo.write(f"FECHA: {fecha_legible}\n")
            archivo.write(f"USUARIO: {nombre}\n")
            archivo.write(f"CORREO: {correo_usuario}\n")
            archivo.write(f"REQUERIMIENTO: {requerimiento}\n")
            archivo.write(f"ARCHIVO ADJUNTO: {nombre_archivo}\n")
            archivo.write(f"========================================\n\n")
        
        # 4. Enviar el correo en SEGUNDO PLANO (HILO APARTE)
        # Esto hace que el usuario no tenga que esperar a que Gmail responda
        hilo = threading.Thread(target=proceso_envio_correo, args=(correo_usuario, ticket_id, nombre, requerimiento))
        hilo.start()
        
        # Interfaz de éxito asegurada
        pantalla_exito = f"""
        <div style="font-family:Arial, sans-serif; text-align:center; margin-top:80px;">
            <div style="max-width:450px; margin:auto; background:#fff; padding:30px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1); border-top: 5px solid #28a745;">
                <h2 style="color:#28a745; margin-bottom:10px;">¡Ticket Generado Exitosamente!</h2>
                <p style="color:#555;">Hola <b>{nombre}</b>, hemos registrado tu requerimiento.</p>
                <p style="color:#777; font-size:14px;">Confirmación enviada al correo: <b>{correo_usuario}</b></p>
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

    except Exception as e:
        # Si algo falla de verdad, nos lo muestra directo en pantalla para no adivinar
        return f"<div style='padding:20px; font-family:sans-serif;'><h3>Ocurrió un error inesperado al procesar tu solicitud:</h3><pre>{str(e)}</pre></div>", 500

@app.route('/ver-base-datos-procesos')
def ver_tickets():
    if not os.path.exists(TICKETS_FILE):
        return "<h3>Aún no se han registrado tickets en el sistema.</h3>"
    with open(TICKETS_FILE, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()
    return f"<pre style='padding:20px; background:#222; color:#fff; font-family:monospace;'>{contenido}</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
