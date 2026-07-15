from flask import Flask, request, render_template, render_template_string, send_from_directory, abort
import os
import random
from datetime import datetime
import smtplib
import ssl
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Configuración de carpetas y base de datos temporal
UPLOAD_FOLDER = '/tmp/evidencias'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TICKETS_FILE = '/tmp/tickets.txt'

# CONFIGURACIÓN DEL CORREO EMISOR Y DESTINATARIO COPIA
CORREO_EMISOR = "msprocesosconfiamoscol@gmail.com"
CORREO_PASSWORD = "ahfq beyj boky zlhz" 
CORREO_COPIA_INSTITUCIONAL = "operacionesyprocesos@confiamoscolombia.com"

def registrar_log_correo(ticket_id, resultado):
    """Guarda en la base de datos si el correo se envió o falló para que puedas revisarlo"""
    try:
        with open(TICKETS_FILE, "a", encoding="utf-8") as archivo:
            archivo.write(f"[SISTEMA CORREO - TICKET {ticket_id}]: {resultado}\n\n")
    except Exception as e:
        print(f"Error escribiendo log de correo: {e}")

def proceso_envio_correo(correo_usuario, ticket_id, usuario, requerimiento):
    """Envía correos individuales para evitar que uno rebote al otro y registra el resultado"""
    
    # 1. Crear el mensaje base
    mensaje_usuario = MIMEMultipart()
    mensaje_usuario['From'] = CORREO_EMISOR
    mensaje_usuario['To'] = correo_usuario
    mensaje_usuario['Subject'] = f"🔔 Confirmación de Ticket: {ticket_id}"
    
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
    mensaje_usuario.attach(MIMEText(cuerpo, 'plain'))

    # Crear el mensaje para operaciones
    mensaje_ops = MIMEMultipart()
    mensaje_ops['From'] = CORREO_EMISOR
    mensaje_ops['To'] = CORREO_COPIA_INSTITUCIONAL
    mensaje_ops['Subject'] = f"🚨 NUEVO TICKET REGISTRADO: {ticket_id}"
    
    cuerpo_ops = f"""
    Atención Equipo de Operaciones,
    
    Se ha recibido un nuevo ticket en la Mesa de Servicio.
    
    DETALLES DEL REPORTE:
    ----------------------------------------
    ID TICKET: {ticket_id}
    USUARIO: {usuario}
    CORREO CONTACTO: {correo_usuario}
    REQUERIMIENTO: {requerimiento}
    ----------------------------------------
    
    Por favor ingresar a la consola de monitoreo para validar las evidencias adjuntas.
    """
    mensaje_ops.attach(MIMEText(cuerpo_ops, 'plain'))
    
    log_final = ""
    
    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto) as server:
            server.login(CORREO_EMISOR, CORREO_PASSWORD)
            
            # Intentar enviar al usuario
            try:
                server.sendmail(CORREO_EMISOR, correo_usuario, mensaje_usuario.as_string())
                log_final += f"Enviado con éxito al usuario ({correo_usuario}). "
            except Exception as e_user:
                log_final += f"FALLÓ envío al usuario. Error: {e_user}. "
                
            # Intentar enviar a operaciones
            try:
                server.sendmail(CORREO_EMISOR, CORREO_COPIA_INSTITUCIONAL, mensaje_ops.as_string())
                log_final += f"Enviado con éxito a Operaciones ({CORREO_COPIA_INSTITUCIONAL})."
            except Exception as e_ops:
                log_final += f"FALLÓ envío a Operaciones. Error: {e_ops}."
                
        registrar_log_correo(ticket_id, f"✅ PROCESO COMPLETADO -> {log_final}")
        
    except Exception as e_conexion:
        # Si ni siquiera pudo iniciar sesión en Gmail
        registrar_log_correo(ticket_id, f"❌ FALLÓ AUTENTICACIÓN EN GMAIL (¿Clave incorrecta?): {e_conexion}")

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
        
        # 1. Guardar archivo adjunto de forma segura
        nombre_archivo = "Sin evidencia"
        if evidencia and evidencia.filename != '':
            nombre_archivo = evidencia.filename
            nombre_archivo = nombre_archivo.replace(" ", "_")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
            evidencia.save(filepath)
        
        # 2. Generar ID único del Ticket
        ahora = datetime.now()
        fecha_ticket = ahora.strftime("%Y%m%d")
        fecha_legible = ahora.strftime("%Y-%m-%d %H:%M:%S")
        numero_aleatorio = random.randint(100, 999)
        ticket_id = f"TK-{fecha_ticket}-{numero_aleatorio}"
        
        # 3. Guardar en la base de datos de texto
        with open(TICKETS_FILE, "a", encoding="utf-8") as archivo:
            archivo.write(f"========================================\n")
            archivo.write(f"TICKET: {ticket_id}\n")
            archivo.write(f"FECHA: {fecha_legible}\n")
            archivo.write(f"USUARIO: {nombre}\n")
            archivo.write(f"CORREO: {correo_usuario}\n")
            archivo.write(f"REQUERIMIENTO: {requerimiento}\n")
            archivo.write(f"ARCHIVO ADJUNTO: {nombre_archivo}\n")
            archivo.write(f"========================================\n\n")
        
        # 4. Enviar notificación por correo en segundo plano
        hilo = threading.Thread(target=proceso_envio_correo, args=(correo_usuario, ticket_id, nombre, requerimiento))
        hilo.start()
        
        pantalla_exito = f"""
        <div style="font-family:Arial, sans-serif; text-align:center; margin-top:80px;">
            <div style="max-width:450px; margin:auto; background:#fff; padding:30px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1); border-top: 5px solid #28a745;">
                <h2 style="color:#28a745; margin-bottom:10px;">¡Ticket Generado Exitosamente!</h2>
                <p style="color:#555;">Hola <b>{nombre}</b>, hemos registrado tu requerimiento.</p>
                <p style="color:#777; font-size:14px;">Se procesará el envío de correo a: <br><b>{correo_usuario}</b><br>y a <b>{CORREO_COPIA_INSTITUCIONAL}</b></p>
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
        return f"<div style='padding:20px; font-family:sans-serif;'><h3>Error detectado:</h3><pre>{str(e)}</pre></div>", 500

# RUTA PARA DESCARGAR O VISUALIZAR LAS EVIDENCIAS ADJUNTAS
@app.route('/descargar-evidencia/<filename>')
def descargar_archivo(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        abort(404, description="El archivo solicitado ya no existe en el almacenamiento temporal.")

# RUTA PARA VER LA BASE DE DATOS DE TICKETS CON ENLACES A LAS EVIDENCIAS
@app.route('/ver-base-datos-procesos')
def ver_tickets():
    if not os.path.exists(TICKETS_FILE):
        return "<h3>Aún no se han registrado tickets en el sistema.</h3>"
        
    with open(TICKETS_FILE, "r", encoding="utf-8") as archivo:
        lineas = archivo.readlines()
        
    contenido_html = []
    for linea in lineas:
        if "ARCHIVO ADJUNTO:" in linea:
            partes = linea.split("ARCHIVO ADJUNTO:")
            nombre_archivo = partes[1].strip()
            
            if nombre_archivo != "Sin evidencia":
                enlace = f"<a href='/descargar-evidencia/{nombre_archivo}' style='color: #00bcd4; text-decoration: underline;' download>{nombre_archivo}</a>"
                linea = f"ARCHIVO ADJUNTO: {enlace}\n"
                
        contenido_html.append(linea)
        
    contenido_final = "".join(contenido_html)
    
    return f"""
    <body style="background:#222; color:#fff; font-family:monospace; padding:20px;">
        <h2>📋 Consola de Monitoreo de Tickets</h2>
        <p style="color:#aaa;">Haz clic sobre el nombre de cualquier archivo adjunto para descargarlo directamente.</p>
        <hr style="border:0; border-top: 1px solid #444; margin-bottom:20px;">
        <pre style='background:#111; padding:20px; border-radius:6px; border: 1px solid #333; overflow-x:auto;'>{contenido_final}</pre>
    </body>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
