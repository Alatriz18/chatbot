from flask import Flask, jsonify, request, send_from_directory, redirect, url_for, send_file
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import pyodbc
import os
import datetime
import logging
from crypto_utils import decrypt_password
from flask_socketio import SocketIO, emit
import threading
import time
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- Configuración ---
app = Flask(__name__, static_url_path='', static_folder='../frontend')
CORS(app, resources={r"/api/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)


socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
NOTIFICATION_SOUNDS_FOLDER = '../frontend/static/notification_sounds'
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}


# --- Configuración de Conexiones ---
POSTGRES_URL = os.getenv("DATABASE_URL")
INFORMIX_URI = (
    f"DRIVER={{IBM INFORMIX ODBC DRIVER (64-bit)}};"
    f"SERVER={os.getenv('INFORMIX_SERVER', 'ol_planta')};"
    f"DATABASE={os.getenv('INFORMIX_DATABASE', 'lasso')};"
    f"HOST={os.getenv('INFORMIX_HOST', '172.20.4.51')};"
    f"PROTOCOL=onsoctcp;"
    f"SERVICE={os.getenv('INFORMIX_PORT', '1526')};"
    f"UID={os.getenv('INFORMIX_USER', 'informix')};"
    f"PWD={os.getenv('INFORMIX_PASSWORD', 'Inf0rm1x_2019_lss')};"
)

# --- Configuración de Archivos ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
MAX_FILE_SIZE = 64 * 1024 * 1024  # 16MB



# Crear directorio de uploads si no existe
os.makedirs(NOTIFICATION_SOUNDS_FOLDER, exist_ok=True)
# Diccionario para mantener seguimiento de administradores conectados
def allowed_audio_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS
@app.route('/static/notification_sounds/<path:filename>')
def serve_notification_sound(filename):
    return send_from_directory(NOTIFICATION_SOUNDS_FOLDER, filename)
connected_admins = {}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_postgres_connection():
    try: return psycopg2.connect(POSTGRES_URL)
    except Exception as e:
        logging.error(f"Error de conexión a PostgreSQL: {e}")
        return None

def get_informix_connection():
    try: return pyodbc.connect(INFORMIX_URI)
    except Exception as e:
        logging.error(f"Error de conexión a Informix: {e}")
        return None

def format_file_size(size_bytes):
    """Convertir bytes a formato legible"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names)-1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


# --- WebSocket Events ---
@socketio.on('connect')
def handle_connect():
    logging.info(f'Cliente conectado: {request.sid}')
    emit('connection_response', {'status': 'connected', 'message': 'Conexión establecida'})

@socketio.on('disconnect')
def handle_disconnect():
    logging.info(f'Cliente desconectado: {request.sid}')
    # Remover de connected_admins si está presente
    for admin, sid in list(connected_admins.items()):
        if sid == request.sid:
            del connected_admins[admin]
            logging.info(f'Administrador {admin} desconectado')
            break

@socketio.on('admin_online')
def handle_admin_online(data):
    admin_username = data.get('username')
    if admin_username:
        connected_admins[admin_username] = request.sid
        logging.info(f'Administrador {admin_username} en línea (SID: {request.sid})')
        emit('admin_status', {'status': 'online', 'message': 'Estado actualizado'})

@socketio.on('join_admin_room')
def handle_join_admin_room(data):
    admin_username = data.get('username')
    if admin_username:
        connected_admins[admin_username] = request.sid
        logging.info(f'Administrador {admin_username} unido a la sala')

def send_notification_to_admin(admin_username, notification_data):
    """Función para enviar notificación a un administrador específico"""
    if admin_username in connected_admins:
        try:
            sid = connected_admins[admin_username]
            socketio.emit('new_ticket_notification', notification_data, room=sid)
            logging.info(f'Notificación enviada al administrador: {admin_username}')
            return True
        except Exception as e:
            logging.error(f"Error enviando notificación a {admin_username}: {e}")
            return False
    else:
        logging.info(f'Administrador {admin_username} no está conectado. Notificación no enviada.')
        return False
@app.route('/api/upload-notification-sound', methods=['POST'])
def upload_notification_sound():
    try:
        print("📢 Recibiendo solicitud de subida de sonido...")
        
        if 'sound' not in request.files:
            print("❌ No se encontró el archivo 'sound'")
            return jsonify({"error": "No se encontró el archivo de sonido"}), 400
        
        file = request.files['sound']
        username = request.form.get('username')
        
        print(f"📁 Archivo recibido: {file.filename}")
        print(f"👤 Usuario: {username}")
        
        if not username:
            return jsonify({"error": "Nombre de usuario requerido"}), 400
        
        if file.filename == '':
            return jsonify({"error": "Nombre de archivo vacío"}), 400
        
        if file and allowed_audio_file(file.filename):
            # Eliminar sonido anterior del usuario si existe
            user_sound_pattern = f"{username}_*"
            for existing_file in os.listdir(NOTIFICATION_SOUNDS_FOLDER):
                if existing_file.startswith(f"{username}_"):
                    old_path = os.path.join(NOTIFICATION_SOUNDS_FOLDER, existing_file)
                    os.remove(old_path)
                    print(f"🗑️ Sonido anterior eliminado: {existing_file}")
            
            # Generar nombre único para el archivo
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{username}_{uuid.uuid4().hex}.{file_extension}"
            file_path = os.path.join(NOTIFICATION_SOUNDS_FOLDER, unique_filename)
            
            # Guardar archivo
            file.save(file_path)
            
            # Devolver la ruta relativa para el frontend
            relative_path = f"/{file_path}"
            
            print(f"✅ Sonido guardado: {unique_filename}")
            
            return jsonify({
                "success": True,
                "message": "Sonido personalizado guardado correctamente",
                "filePath": relative_path,
                "filename": unique_filename
            })
        else:
            print("❌ Tipo de archivo no permitido")
            return jsonify({"error": "Tipo de archivo no permitido. Use: MP3, WAV, OGG, M4A"}), 400
            
    except Exception as e:
        print(f"💥 Error al subir sonido: {e}")
        logging.error(f"Error al subir sonido personalizado: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-notification-sound', methods=['POST'])
def delete_notification_sound():
    try:
        data = request.json
        username = data.get('username')
        
        if not username:
            return jsonify({"error": "Nombre de usuario requerido"}), 400
        
        # Buscar y eliminar sonidos del usuario
        deleted_files = []
        for filename in os.listdir(NOTIFICATION_SOUNDS_FOLDER):
            if filename.startswith(f"{username}_"):
                file_path = os.path.join(NOTIFICATION_SOUNDS_FOLDER, filename)
                os.remove(file_path)
                deleted_files.append(filename)
        
        print(f"🗑️ Sonidos eliminados para {username}: {deleted_files}")
        
        return jsonify({
            "success": True,
            "message": f"Se eliminaron {len(deleted_files)} archivos de sonido",
            "deletedFiles": deleted_files
        })
        
    except Exception as e:
        print(f"💥 Error al eliminar sonidos: {e}")
        logging.error(f"Error al eliminar sonidos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-notification-sound', methods=['GET'])
def get_notification_sound():
    try:
        username = request.args.get('username')
        
        if not username:
            return jsonify({"error": "Nombre de usuario requerido"}), 400
        
        # Buscar sonido del usuario
        user_sound = None
        for filename in os.listdir(NOTIFICATION_SOUNDS_FOLDER):
            if filename.startswith(f"{username}_"):
                user_sound = f"/{NOTIFICATION_SOUNDS_FOLDER}/{filename}"
                break
        
        return jsonify({
            "success": True,
            "hasCustomSound": user_sound is not None,
            "soundPath": user_sound
        })
        
    except Exception as e:
        print(f"💥 Error al obtener sonido: {e}")
        logging.error(f"Error al obtener sonido: {e}")
        return jsonify({"error": str(e)}), 500
# --- Rutas para servir páginas ---
@app.route('/')
def serve_root(): return send_from_directory('../frontend', 'login.html')
@app.route('/admin')
def serve_admin_page(): return send_from_directory('../frontend', 'admin.html')
@app.route('/chat')
def serve_chat_page(): return send_from_directory('../frontend', 'chat.html')

# --- API Endpoints ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username_from_form = data.get('username')
    password_from_form = data.get('password')
    if not username_from_form or not password_from_form:
        return jsonify({"error": "Usuario y contraseña son requeridos"}), 400
    conn = get_informix_connection()
    if not conn:
        return jsonify({"error": "Error de conexión con el servidor de autenticación"}), 500
    try:
        with conn.cursor() as cur:
            sql_get_user_code = "SELECT usua_cod_usua FROM saeusua WHERE usua_nom_usua = ?"
            cur.execute(sql_get_user_code, (username_from_form,))
            user_code_row = cur.fetchone()
            if not user_code_row: return jsonify({"error": "Usuario o contraseña incorrectos"}), 401
            user_code = user_code_row[0]
            sql_get_pass_and_role = "SELECT respu_pas_usua, respu_rol_usua FROM gerespu WHERE respu_cod_usua = ?"
            cur.execute(sql_get_pass_and_role, (user_code,))
            user_info_row = cur.fetchone()
            if not user_info_row: return jsonify({"error": "Usuario o contraseña incorrectos"}), 401
            encrypted_password_from_db = user_info_row[0]
            role_from_db = user_info_row[1].strip() if user_info_row[1] else ""
            final_user_role = 'admin' if role_from_db == 'A' else 'user'
            password_blob = encrypted_password_from_db.encode('latin-1') if isinstance(encrypted_password_from_db, str) else encrypted_password_from_db
            decrypted_password = decrypt_password(password_blob)
            if decrypted_password == password_from_form:
                user_data = {"username": username_from_form, "rol": final_user_role, "user_code": user_code}
                return jsonify({"success": True, "user": user_data})
            else:
                return jsonify({"error": "Usuario o contraseña incorrectos"}), 401
    except Exception as e:
        logging.error(f"Excepción durante la autenticación para {username_from_form}: {e}")
        return jsonify({"error": "Ocurrió un error crítico en el servidor"}), 500
    finally:
        if conn: conn.close()

@app.route('/api/admins', methods=['GET'])
def get_admins():
    conn_informix = get_informix_connection()
    if not conn_informix:
        return jsonify({"error": "No se pudo conectar al servidor de usuarios"}), 500
    
    admins = []
    try:
        with conn_informix.cursor() as cur:
            sql = """
                SELECT r.respu_cod_usua, s.usua_nom_usua 
                FROM gerespu r
                JOIN saeusua s ON r.respu_cod_usua = s.usua_cod_usua
                WHERE r.respu_rol_usua = 'A'
            """
            cur.execute(sql)
            for row in cur.fetchall():
                admins.append({"user_code": row[0], "username": row[1].strip()})
        return jsonify(admins)
    except Exception as e:
        logging.error(f"Error al obtener la lista de administradores: {e}")
        return jsonify({"error": "Error interno al consultar administradores"}), 500
    finally:
        if conn_informix: conn_informix.close()

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    data = request.json
    user_data = data.get('context', {})
    user_info = data.get('user', {})
    user_code = user_info.get('user_code')
    
  
    preferred_admin = data.get('preferred_admin')  # Cambiado de user_data a data
    
    assigned_to = None

    # --- LÓGICA DE ASIGNACIÓN AUTOMÁTICA MEJORADA ---
    if preferred_admin and preferred_admin != 'none':
        assigned_to = preferred_admin
        logging.info(f"Ticket asignado por preferencia del usuario a: {assigned_to}")
    else:
        conn_postgres = get_postgres_connection()
        conn_informix = get_informix_connection()
        
        if conn_postgres and conn_informix:
            try:
                with conn_informix.cursor() as cur_i:
                    sql_admins = """
                        SELECT s.usua_nom_usua 
                        FROM gerespu r 
                        JOIN saeusua s ON r.respu_cod_usua = s.usua_cod_usua 
                        WHERE r.respu_rol_usua = 'A'
                    """
                    cur_i.execute(sql_admins)
                    all_admins = [row[0].strip() for row in cur_i.fetchall()]

                if all_admins:
                    with conn_postgres.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_p:
                        sql_counts = """
                            SELECT ticket_asignado_a, COUNT(*) as ticket_count
                            FROM soporte_ti.stticket
                            WHERE ticket_est_ticket != 'FN' AND ticket_asignado_a IS NOT NULL
                            GROUP BY ticket_asignado_a;
                        """
                        cur_p.execute(sql_counts)
                        ticket_counts = {row['ticket_asignado_a']: row['ticket_count'] for row in cur_p.fetchall()}

                   
                    available_admins = [admin for admin in all_admins if admin in ticket_counts or admin not in ticket_counts]
                    
                    if available_admins:
                        min_tickets = float('inf')
                        least_busy_admin = available_admins[0]
                        
                        for admin in available_admins:
                            count = ticket_counts.get(admin, 0)  # Si no tiene tickets, count = 0
                            if count < min_tickets:
                                min_tickets = count
                                least_busy_admin = admin
                        
                        assigned_to = least_busy_admin
                        logging.info(f"Asignación automática a: {assigned_to} (con {min_tickets} tickets)")
                    else:
                        # Si no hay admins disponibles, asignar al primero de la lista
                        assigned_to = all_admins[0] if all_admins else None
                        logging.info(f"Asignación por defecto a: {assigned_to}")
                        
                else:
                    logging.warning("No se encontraron administradores para la asignación automática.")
                    
            except Exception as e:
                logging.error(f"Error en la asignación automática: {e}")
                # En caso de error, asignar por defecto si hay admins
                if all_admins:
                    assigned_to = all_admins[0]
            finally:
                if conn_postgres: conn_postgres.close()
                if conn_informix: conn_informix.close()
        else:
            logging.error("No se pudieron establecer conexiones a las bases de datos")
    
    conn = get_postgres_connection()
    if not conn:
        return jsonify({"error": "Error de base de datos"}), 500

    problem_description = user_data.get('problemDescription', 'N/A')
    final_options_tried = user_data.get('finalOptionsTried', [])
    
    options_text = ""
    if final_options_tried:
        options_text += "\n\n--- Opciones Finales Intentadas sin Éxito ---\n"
        for option in final_options_tried:
            options_text += f"- {option}\n"

    final_description = f"{problem_description}{options_text}"

    ticket_id_str = f"TKT-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    categoria_key = user_data.get('categoryKey', '')
    tipo_ticket = 'Software' if 'software' in categoria_key.lower() else 'Hardware'
    
   
    sql = """
        INSERT INTO soporte_ti.stticket 
        (ticket_des_ticket, ticket_id_ticket, ticket_tip_ticket, ticket_est_ticket, 
         ticket_asu_ticket, ticket_tusua_ticket, ticket_cie_ticket, ticket_asignado_a, ticket_preferencia_usuario)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                final_description,
                ticket_id_str, 
                tipo_ticket, 
                'PE',
                user_data.get('subcategoryKey', 'Sin asunto'),
                user_info.get('username', 'No especificado'),
                user_code,
                assigned_to,  
                preferred_admin  
            ))
            conn.commit()
          # --- ENVÍO DE NOTIFICACIÓN EN TIEMPO REAL ---
        if assigned_to:
            notification_data = {
                'type': 'new_ticket',
                'title': '🎫 Nuevo Ticket Asignado',
                'message': f'Se te ha asignado el ticket: {ticket_id_str}',
                'ticket_id': ticket_id_str,
                'assigned_to': assigned_to,
                'user': user_info.get('username', 'Usuario'),
                'subject': user_data.get('subcategoryKey', 'Sin asunto'),
                'timestamp': datetime.datetime.now().isoformat(),
                'category': tipo_ticket
            }
            
            # Intentar enviar notificación en tiempo real
            notification_sent = send_notification_to_admin(assigned_to, notification_data)
            
            if not notification_sent:
                logging.info(f"El administrador {assigned_to} no está conectado. La notificación se mostrará cuando se conecte.")
        
        return jsonify({
            "success": True, 
            "ticket_id": ticket_id_str, 
            "assigned_to": assigned_to,
            "preferred_admin": preferred_admin,
            "notification_sent": assigned_to in connected_admins if assigned_to else False
        }), 201
        
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al crear ticket: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
# --- SISTEMA DE ARCHIVOS ADJUNTOS ---

@app.route('/api/tickets/<string:ticket_id>/upload', methods=['POST'])
def upload_file(ticket_id):
    """Endpoint para subir archivos adjuntos a un ticket"""
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró el archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    
    if file and allowed_file(file.filename):
        # Verificar tamaño del archivo
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE//1024//1024}MB"}), 400
        
        # Crear estructura de carpetas organizada por ticket
        ticket_folder = os.path.join(UPLOAD_FOLDER, ticket_id)
        os.makedirs(ticket_folder, exist_ok=True)
        
        # Generar nombre único pero manteniendo la extensión original
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(ticket_folder, unique_filename)
        
        # Guardar archivo en sistema de archivos
        file.save(file_path)
        
        # Registrar metadatos en base de datos
        conn = get_postgres_connection()
        if not conn:
            # Limpiar archivo si falla la BD
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": "Error de base de datos"}), 500
        
        try:
           with conn.cursor() as cur:
                # PRIMERO: Obtener el ticket_cod_ticket (INTEGER) de la tabla stticket
                cur.execute("""
                    SELECT ticket_cod_ticket 
                    FROM soporte_ti.stticket 
                    WHERE ticket_id_ticket = %s
                """, (ticket_id,))
                
                ticket_record = cur.fetchone()
                if not ticket_record:
                    # Limpiar archivo si el ticket no existe
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return jsonify({"error": "Ticket no encontrado"}), 404
                
                ticket_cod_ticket = ticket_record[0]  # Este es el INTEGER que necesitas
                
                # AHORA INSERTAR con el ticket_cod_ticket correcto
                cur.execute("""
                    INSERT INTO soporte_ti.starchivos 
                    (archivo_cod_ticket, archivo_nom_archivo, archivo_tip_archivo, 
                     archivo_tam_archivo, archivo_rut_archivo, archivo_usua_archivo) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (ticket_cod_ticket, file.filename, file_extension, file_size, 
                      f"{ticket_id}/{unique_filename}", request.form.get('username', 'Sistema')))
                
                conn.commit()
                
                # Obtener el ID del archivo recién insertado
                cur.execute("SELECT currval('soporte_ti.starchivos_archivo_cod_archivo_seq')")
                file_id = cur.fetchone()[0]
            
                return jsonify({
                    "success": True, 
                    "message": "Archivo subido correctamente",
                    "file_id": file_id,
                    "filename": file.filename,
                    "file_size": format_file_size(file_size)
                })
                
        except Exception as e:
            conn.rollback()
            # Eliminar archivo físico si falla la inserción en BD
            if os.path.exists(file_path):
                os.remove(file_path)
            logging.error(f"Error al subir archivo: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            if conn: conn.close()
    else:
        return jsonify({"error": "Tipo de archivo no permitido"}), 400

@app.route('/api/tickets/<string:ticket_id>/files', methods=['GET'])
def get_ticket_files(ticket_id):
    """Obtener lista de archivos adjuntos de un ticket"""
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Primero obtener el ticket_cod_ticket
            cur.execute("""
                SELECT ticket_cod_ticket 
                FROM soporte_ti.stticket 
                WHERE ticket_id_ticket = %s
            """, (ticket_id,))
            
            ticket_record = cur.fetchone()
            if not ticket_record:
                return jsonify({"error": "Ticket no encontrado"}), 404
            
            ticket_cod_ticket = ticket_record[0]
            
            # Luego buscar los archivos usando el ID numérico
            cur.execute("""
                SELECT archivo_cod_archivo, archivo_nom_archivo, archivo_tip_archivo, 
                       archivo_tam_archivo, archivo_usua_archivo, archivo_fec_archivo 
                FROM soporte_ti.starchivos 
                WHERE archivo_cod_ticket = %s 
                ORDER BY archivo_fec_archivo DESC
            """, (ticket_cod_ticket,))
            
            files = []
            for row in cur.fetchall():
                file_data = dict(row)
                file_data['archivo_tam_formateado'] = format_file_size(file_data['archivo_tam_archivo'])
                file_data['archivo_fec_formateada'] = file_data['archivo_fec_archivo'].strftime('%Y-%m-%d %H:%M:%S')
                files.append(file_data)
            
            return jsonify(files)
    except Exception as e:
        logging.error(f"Error al obtener archivos del ticket {ticket_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/files/<int:file_id>/download')
def download_file(file_id):
    """Descargar un archivo adjunto"""
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT archivo_nom_archivo, archivo_rut_archivo, archivo_tip_archivo 
                FROM soporte_ti.starchivos 
                WHERE archivo_cod_archivo = %s
            """, (file_id,))
            
            file_record = cur.fetchone()
            if not file_record:
                return jsonify({"error": "Archivo no encontrado"}), 404
            
            file_path = os.path.join(UPLOAD_FOLDER, file_record['archivo_rut_archivo'])
            
            if not os.path.exists(file_path):
                logging.error(f"Archivo físico no encontrado: {file_path}")
                return jsonify({"error": "Archivo físico no encontrado"}), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=file_record['archivo_nom_archivo']
            )
            
    except Exception as e:
        logging.error(f"Error al descargar archivo {file_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/files/<int:file_id>/view')
def view_file(file_id):
    """Visualizar un archivo directamente en el navegador (para imágenes, PDFs)"""
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT archivo_nom_archivo, archivo_rut_archivo, archivo_tip_archivo 
                FROM soporte_ti.starchivos 
                WHERE archivo_cod_archivo = %s
            """, (file_id,))
            
            file_record = cur.fetchone()
            if not file_record:
                return jsonify({"error": "Archivo no encontrado"}), 404
            
            file_path = os.path.join(UPLOAD_FOLDER, file_record['archivo_rut_archivo'])
            
            if not os.path.exists(file_path):
                return jsonify({"error": "Archivo físico no encontrado"}), 404
            
            # Determinar el MIME type adecuado
            mime_types = {
                'pdf': 'application/pdf',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'txt': 'text/plain'
            }
            
            mime_type = mime_types.get(file_record['archivo_tip_archivo'], 'application/octet-stream')
            
            return send_file(
                file_path,
                mimetype=mime_type
            )
            
    except Exception as e:
        logging.error(f"Error al visualizar archivo {file_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Eliminar un archivo adjunto"""
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Obtener información del archivo
            cur.execute("""
                SELECT archivo_rut_archivo, archivo_cod_ticket 
                FROM soporte_ti.starchivos 
                WHERE archivo_cod_archivo = %s
            """, (file_id,))
            
            file_record = cur.fetchone()
            if not file_record:
                return jsonify({"error": "Archivo no encontrado"}), 404
            
            # Eliminar registro de la base de datos
            cur.execute("DELETE FROM soporte_ti.starchivos WHERE archivo_cod_archivo = %s", (file_id,))
            conn.commit()
            
            # Eliminar archivo físico
            file_path = os.path.join(UPLOAD_FOLDER, file_record['archivo_rut_archivo'])
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Archivo físico eliminado: {file_path}")
            
            return jsonify({"success": True, "message": "Archivo eliminado correctamente"})
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al eliminar archivo {file_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- ENDPOINTS EXISTENTES (se mantienen igual) ---

@app.route('/api/tickets/log-solved', methods=['POST'])
def log_solved_ticket():
    data = request.json
    user_data = data.get('context', {})
    user_info = data.get('user', {})
   
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500

    ticket_id_str = f"TKT-SOL-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    categoria_key = user_data.get('categoryKey', '')
    tipo_ticket = 'Software' if 'software' in categoria_key.lower() else 'Hardware'
    
    sql = """
        INSERT INTO soporte_ti.stticket 
        (ticket_des_ticket, ticket_id_ticket, ticket_tip_ticket, ticket_est_ticket, ticket_asu_ticket, ticket_tusua_ticket)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                "Resuelto por el usuario a través del Asistente Virtual.",
                ticket_id_str, tipo_ticket, 'FN',
                user_data.get('subcategoryKey', 'Sin asunto'),
                user_info.get('username', 'No especificado')
            ))
            conn.commit()
        return jsonify({"success": True, "ticket_id": ticket_id_str}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/admin/tickets/<string:ticket_id>/assign', methods=['POST'])
def assign_ticket(ticket_id):
    data = request.json
    admin_username = data.get('admin_username')
    if not admin_username:
        return jsonify({"error": "Nombre de usuario del administrador es requerido"}), 400

    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500

    sql = "UPDATE soporte_ti.stticket SET ticket_asignado_a = %s WHERE ticket_id_ticket = %s;"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (admin_username, ticket_id))
            conn.commit()
        return jsonify({"success": True, "message": f"Ticket {ticket_id} asignado a {admin_username}"})
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al asignar ticket {ticket_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/admin/tickets', methods=['GET'])
def get_all_tickets():
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500
    sql = """
        SELECT ticket_id_ticket, ticket_asu_ticket, ticket_est_ticket, ticket_des_ticket, 
               ticket_fec_ticket, ticket_tusua_ticket, ticket_asignado_a 
        FROM soporte_ti.stticket 
        ORDER BY ticket_fec_ticket DESC;
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql)
            tickets = [dict(row) for row in cur.fetchall()]
        return jsonify(tickets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/user/tickets', methods=['GET'])
def get_user_tickets():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Nombre de usuario es requerido"}), 400

    conn = get_postgres_connection()
    if not conn:
        return jsonify({"error": "Error de base de datos"}), 500

    sql = """
        SELECT ticket_id_ticket, ticket_asu_ticket, ticket_est_ticket,ticket_des_ticket, ticket_fec_ticket, ticket_calificacion  
        FROM soporte_ti.stticket 
        WHERE ticket_tusua_ticket = %s 
        ORDER BY ticket_fec_ticket DESC;
    """
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (username,))
            tickets = [dict(row) for row in cur.fetchall()]
            return jsonify(tickets)
    except Exception as e:
        logging.error(f"Error al obtener tickets para {username}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/tickets/<string:ticket_id>', methods=['PUT'])
def update_ticket_status(ticket_id):
    data = request.json
    new_status = data.get('status')
    if not new_status: return jsonify({"error": "Falta el nuevo estado"}), 400
    conn = get_postgres_connection()
    if not conn: return jsonify({"error": "Error de base de datos"}), 500
    sql = "UPDATE soporte_ti.stticket SET ticket_est_ticket = %s WHERE ticket_id_ticket = %s;"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (new_status, ticket_id))
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/log/interaction', methods=['POST'])
def log_interaction():
    data = request.json
    
    session_id = data.get('sessionId')
    username = data.get('username')
    action_type = data.get('actionType')
    action_value = data.get('actionValue')
    bot_response = data.get('botResponse')

    if not session_id or not username:
        return jsonify({"error": "Faltan datos de sesión"}), 400

    conn = get_postgres_connection()
    if not conn:
        return jsonify({"error": "Error de base de datos"}), 500

    sql = """
        INSERT INTO soporte_ti.stlogchat 
        (session_id, username, action_type, action_value, bot_response)
        VALUES (%s, %s, %s, %s, %s);
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, username, action_type, action_value, bot_response))
            conn.commit()
        return jsonify({"success": True}), 201
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al registrar interacción para {username}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tickets/<string:ticket_id>/rate', methods=['POST'])
def rate_ticket(ticket_id):
    data = request.json
    rating = data.get('rating')

    if not isinstance(rating, int) or not 1 <= rating <= 5:
        return jsonify({"error": "La calificación debe ser un número entre 1 y 5"}), 400

    conn = get_postgres_connection()
    if not conn:
        return jsonify({"error": "Error de base de datos"}), 500

    sql = "UPDATE soporte_ti.stticket SET ticket_calificacion = %s WHERE ticket_id_ticket = %s;"
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (rating, ticket_id))
            conn.commit()
        return jsonify({"success": True, "message": "Calificación guardada"})
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al guardar calificación para el ticket {ticket_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Obtener todos los usuarios del sistema"""
    conn_informix = get_informix_connection()
    if not conn_informix:
        return jsonify({"error": "No se pudo conectar al servidor de usuarios"}), 500
    
    users = []
    try:
        with conn_informix.cursor() as cur:
            sql = """
                SELECT s.usua_cod_usua, s.usua_nom_usua 
                FROM saeusua s
                ORDER BY s.usua_nom_usua
            """
            cur.execute(sql)
            for row in cur.fetchall():
                users.append({
                    "user_code": row[0], 
                    "username": row[1].strip() if row[1] else ""
                })
        return jsonify(users)
    except Exception as e:
        logging.error(f"Error al obtener la lista de usuarios: {e}")
        return jsonify({"error": "Error interno al consultar usuarios"}), 500
    finally:
        if conn_informix: conn_informix.close()

@app.route('/api/admin/tickets/<string:ticket_id>/reassign', methods=['POST'])
def reassign_ticket_user(ticket_id):
    """Reasignar el usuario de un ticket"""
    data = request.json
    new_username = data.get('username')
    
    if not new_username:
        return jsonify({"error": "Nombre de usuario es requerido"}), 400

    conn = get_postgres_connection()
    if not conn:
        return jsonify({"error": "Error de base de datos"}), 500

    sql = "UPDATE soporte_ti.stticket SET ticket_tusua_ticket = %s WHERE ticket_id_ticket = %s;"
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (new_username, ticket_id))
            conn.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Ticket {ticket_id} reasignado al usuario {new_username}"
        })
        
    except Exception as e:
        conn.rollback()
        logging.error(f"Error al reasignar ticket {ticket_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
     socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)