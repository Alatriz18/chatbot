import logging
import json
import csv
import datetime
import os
import time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler, ConversationHandler

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Constantes y Configuración ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7375336597:AAFL8wRI0462-lXECPNFQSoI2kZNbWLMphg")
POLITICAS_FILE = 'politicas_ti.json'
TICKETS_FILE = 'tickets_soporte.csv'
TICKETS_LOCK_FILE = 'tickets_soporte.lock'

# --- ROL DE ADMINISTRADOR ---
ADMIN_USER_IDS = [1510724514]  # Reemplaza con tu ID de Telegram

# --- Estados de la Conversación ---
(
    SELECTING_ACTION,
    SELECTING_CATEGORY,
    SELECTING_SUBCATEGORY,
    DESCRIBING_ISSUE,
    CONFIRMING_TICKET
) = range(5)

# --- Carga de Políticas ---
try:
    with open(POLITICAS_FILE, 'r', encoding='utf-8') as f:
        POLITICAS = json.load(f)
except Exception as e:
    logger.error(f"Error al cargar políticas desde {POLITICAS_FILE}: {e}")
    POLITICAS = {
        "casos_soporte": {
            "hardware": {
                "titulo": "Problemas de Hardware",
                "categorias": ["Equipo no enciende", "Pantalla azul/errores", "Problemas con periféricos (teclado/mouse)"]
            },
            "software": {
                "titulo": "Problemas de Software",
                "categorias": ["No puedo instalar un programa", "Error al abrir aplicación", "Problema con Office 365", "Otro"]
            }
        }
    }

# --- Teclados de la Interfaz ---
main_keyboard = [
    ["🎫 Crear Ticket de Soporte", "📋 Consultar Políticas"],
    ["📊 Ver Mis Tickets", "❓ Ayuda"]
]
main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

politicas_keyboard = [
    ["🔒 Ciberseguridad", "💾 Respaldo"],
    ["🔧 Mantenimiento", "📱 Control Apps"],
    ["📋 Licencias", "🛡️ Antivirus"],
    ["🔑 Credenciales", "🚪 Acceso Físico"],
    ["🌐 Redes", "💻 Sistemas"],
    ["📧 Correo", "📶 Internet"],
    ["📊 Clasificación", "🔐 Contraseñas"],
    ["⚖️ Sanciones", "🔙 Menú Principal"]
]
politicas_markup = ReplyKeyboardMarkup(politicas_keyboard, resize_keyboard=True)

# --- Funciones de Manejo de Archivos (Tickets) ---

def acquire_lock():
    """Adquiere un bloqueo para evitar escrituras concurrentes en el archivo CSV."""
    for _ in range(5):
        try:
            with open(TICKETS_LOCK_FILE, 'x'):
                return True
        except FileExistsError:
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error al adquirir bloqueo: {e}")
            break
    return False

def release_lock():
    """Libera el bloqueo del archivo."""
    try:
        if os.path.exists(TICKETS_LOCK_FILE):
            os.remove(TICKETS_LOCK_FILE)
    except Exception as e:
        logger.error(f"Error al liberar bloqueo: {e}")

def clean_csv_duplicates():
    """Limpia el archivo CSV de entradas duplicadas."""
    if not os.path.exists(TICKETS_FILE):
        return
    
    if not acquire_lock():
        logger.warning("No se pudo adquirir bloqueo para limpiar duplicados.")
        return
    
    try:
        # Leer todo el contenido del archivo
        with open(TICKETS_FILE, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Convertir a líneas
        lines = content.strip().split('\n')
        if not lines:
            return
        
        # Mantener encabezados
        headers = lines[0]
        seen_ids = set()
        unique_lines = [headers]
        
        # Procesar cada línea (empezando desde la 1)
        for line in lines[1:]:
            if not line.strip():
                continue
                
            # Extraer el ID del ticket (primera columna)
            parts = line.split(',')
            if parts and len(parts) > 0:
                ticket_id = parts[0].strip().strip('"\'')
                
                # Si es un ID único, agregar a la lista
                if ticket_id and ticket_id not in seen_ids:
                    seen_ids.add(ticket_id)
                    unique_lines.append(line)
        
        # Escribir de vuelta solo las líneas únicas
        with open(TICKETS_FILE, 'w', encoding='utf-8', newline='') as f:
            f.write('\n'.join(unique_lines))
            
        logger.info(f"Limpieza completada. Se mantuvieron {len(unique_lines)-1} tickets únicos.")
        
    except Exception as e:
        logger.error(f"Error al limpiar duplicados: {e}")
    finally:
        release_lock()

def init_tickets_file():
    """Inicializa el archivo CSV de tickets, creando el encabezado si no existe."""
    if not acquire_lock():
        logger.warning("No se pudo adquirir bloqueo para inicializar el archivo de tickets.")
        return
    
    try:
        # Limpiar duplicados primero
        if os.path.exists(TICKETS_FILE):
            clean_csv_duplicates()
        else:
            # Crear nuevo archivo
            with open(TICKETS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'fecha', 'usuario', 'user_id', 'categoria', 'subcategoria', 'problema', 'estado', 'prioridad'])
            logger.info("Archivo de tickets creado exitosamente.")
            
    except Exception as e:
        logger.error(f"Error al inicializar el archivo de tickets: {e}")
    finally:
        release_lock()

def save_ticket(user_data: dict) -> str | None:
    """Guarda un nuevo ticket en el archivo CSV."""
    if not acquire_lock():
        logger.error("No se pudo adquirir bloqueo para guardar el ticket.")
        return None
    
    try:
        ticket_id = f"TKT-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        fecha = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        prioridad = "Media"
        categoria_lower = user_data.get('categoria', '').lower()
        if any(word in categoria_lower for word in ["red", "internet", "correo", "acceso", "sistema", "servidor"]):
            prioridad = "Alta"
        elif any(word in categoria_lower for word in ["hardware", "impresora", "periféricos"]):
            prioridad = "Baja"
        
        with open(TICKETS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                ticket_id,
                fecha,
                user_data.get('username', 'N/A'),
                user_data.get('user_id', 'N/A'),
                user_data.get('categoria', 'N/A'),
                user_data.get('subcategoria', 'N/A'),
                user_data.get('problema', 'N/A'),
                'Abierto',
                prioridad
            ])
        logger.info(f"Ticket {ticket_id} guardado para el usuario {user_data.get('username')}")
        return ticket_id
    except Exception as e:
        logger.error(f"Error al guardar ticket: {e}")
        return None
    finally:
        release_lock()

def get_user_tickets(user_id: int) -> list:
    """Obtiene todos los tickets de un usuario, asegurando que no haya duplicados."""
    tickets = []
    seen_ids = set()
    
    if not os.path.exists(TICKETS_FILE):
        return tickets

    if not acquire_lock():
        logger.warning("No se pudo adquirir bloqueo para leer tickets.")
        return tickets
        
    try:
        # Leer el archivo como texto para manejar BOM
        with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remover BOM si existe
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # Convertir a líneas
        lines = content.strip().split('\n')
        if not lines:
            return tickets
        
        # Procesar encabezados
        headers = [h.strip().strip('"\'') for h in lines[0].split(',')]
        if 'id' not in headers or 'user_id' not in headers:
            logger.error("Encabezados del CSV no válidos")
            return tickets
        
        # Procesar cada línea de datos
        for line in lines[1:]:
            if not line.strip():
                continue
                
            # Parsear la línea manualmente
            parts = line.split(',')
            if len(parts) < len(headers):
                continue
                
            # Crear diccionario con los datos
            row = {}
            for i, header in enumerate(headers):
                if i < len(parts):
                    row[header] = parts[i].strip().strip('"\'')
                else:
                    row[header] = ''
            
            # Verificar que sea un ticket válido del usuario
            ticket_id = row.get('id', '')
            row_user_id = row.get('user_id', '')
            
            if (ticket_id and row_user_id == str(user_id) and 
                ticket_id not in seen_ids):
                tickets.append(row)
                seen_ids.add(ticket_id)
        
        # Ordenar por fecha (más recientes primero)
        tickets.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
    except Exception as e:
        logger.error(f"Error al leer el archivo de tickets: {e}")
    finally:
        release_lock()
    
    return tickets

# --- Handlers de Comandos y Menú Principal ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación y muestra el menú principal."""
    user = update.effective_user
    context.user_data['username'] = user.full_name
    context.user_data['user_id'] = user.id
    
    await update.message.reply_html(
        rf"👋 ¡Hola {user.mention_html()}! Soy tu asistente de Soporte Técnico y Políticas de TI. ¿En qué puedo ayudarte hoy?",
        reply_markup=main_markup
    )
    return SELECTING_ACTION

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra un mensaje de ayuda."""
    help_text = """
🛡️ <b>Bot de Soporte Técnico y Políticas de TI</b>

<b>Funciones principales:</b>
• 🎫 <b>Crear Ticket de Soporte</b>: Para reportar cualquier problema técnico.
• 📋 <b>Consultar Políticas</b>: Accede a la información sobre las políticas de TI.
• 📊 <b>Ver Mis Tickets</b>: Revisa el estado y el historial de tus tickets.
• /cancel: Anula la operación actual.

<b>Comandos de Administrador:</b>
• /ver_tickets [user_id]: Muestra los tickets de un usuario específico.
• /limpiar_duplicados: Limpia tickets duplicados del sistema.
"""
    await update.message.reply_html(help_text, reply_markup=main_markup)
    return SELECTING_ACTION

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Regresa al menú principal."""
    await update.message.reply_text("🔙 Menú Principal. ¿Qué deseas hacer?", reply_markup=main_markup)
    return SELECTING_ACTION

# --- Flujo de Creación de Tickets ---

async def handle_main_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección del usuario en el menú principal."""
    text = update.message.text
    
    if text == "🎫 Crear Ticket de Soporte":
        return await start_ticket_creation(update, context)
    elif text == "📋 Consultar Políticas":
        await update.message.reply_html("📚 <b>Selecciona la política que deseas consultar:</b>", reply_markup=politicas_markup)
        return SELECTING_ACTION
    elif text == "📊 Ver Mis Tickets":
        return await view_my_tickets(update, context)
    elif text == "❓ Ayuda":
        return await help_command(update, context)
    elif text == "🔙 Menú Principal":
        return await main_menu(update, context)
    else:
        return await handle_policy_query(update, context)

async def start_ticket_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de creación de tickets mostrando las categorías principales."""
    # Limpiar datos previos
    for key in ['categoria', 'subcategoria', 'problema']:
        if key in context.user_data:
            del context.user_data[key]
    
    categorias = [
        [InlineKeyboardButton(value['titulo'], callback_data=key)]
        for key, value in POLITICAS.get('casos_soporte', {}).items()
    ]
    
    if not categorias:
        await update.message.reply_text("⚠️ No hay categorías de soporte disponibles.", reply_markup=main_markup)
        return SELECTING_ACTION
    
    reply_markup = InlineKeyboardMarkup(categorias)
    await update.message.reply_html("🛠️ <b>Paso 1: Selecciona la categoría general:</b>", reply_markup=reply_markup)
    return SELECTING_CATEGORY

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de la categoría principal y muestra las subcategorías."""
    query = update.callback_query
    await query.answer()
    
    categoria_key = query.data
    category_data = POLITICAS.get('casos_soporte', {}).get(categoria_key, {})
    
    if not category_data:
        await query.edit_message_text("❌ Categoría no válida.", reply_markup=main_markup)
        return SELECTING_ACTION
    
    context.user_data['categoria'] = category_data.get('titulo')
    context.user_data['categoria_key'] = categoria_key
    
    subcategorias = [
        [InlineKeyboardButton(subcat, callback_data=subcat)]
        for subcat in category_data.get('categorias', [])
    ]
    subcategorias.append([InlineKeyboardButton("🔙 Volver a categorías", callback_data="back_to_categories")])
    
    reply_markup = InlineKeyboardMarkup(subcategorias)
    await query.edit_message_text(
        "🔍 <b>Paso 2: Selecciona el tipo de problema específico:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECTING_SUBCATEGORY

async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de la subcategoría y pide la descripción del problema."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_categories":
        categorias = [
            [InlineKeyboardButton(value['titulo'], callback_data=key)]
            for key, value in POLITICAS.get('casos_soporte', {}).items()
        ]
        reply_markup = InlineKeyboardMarkup(categorias)
        await query.edit_message_text(
            "🛠️ <b>Paso 1: Selecciona la categoría general de tu problema:</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return SELECTING_CATEGORY

    context.user_data['subcategoria'] = query.data
    await query.edit_message_text(
        "📝 <b>Paso 3: Describe tu problema con el mayor detalle posible.</b>\n\n"
        "<i>Ej: 'Mi laptop no enciende. He probado a conectarla en otro enchufe pero no responde.'</i>",
        parse_mode='HTML'
    )
    return DESCRIBING_ISSUE

async def handle_problem_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la descripción del problema y muestra un resumen para confirmación."""
    main_menu_buttons = ["🎫 Crear Ticket de Soporte", "📋 Consultar Políticas", "📊 Ver Mis Tickets", "❓ Ayuda", "🔙 Menú Principal"]
    if update.message.text in main_menu_buttons:
        return await handle_main_selection(update, context)
        
    context.user_data['problema'] = update.message.text
    
    resumen = (
        "📋 <b>Resumen de tu ticket (Paso 4):</b>\n\n"
        f"👤 <b>Usuario:</b> {context.user_data.get('username', 'N/A')}\n"
        f"🏷️ <b>Categoría:</b> {context.user_data.get('categoria', 'N/A')}\n"
        f"🔍 <b>Tipo:</b> {context.user_data.get('subcategoria', 'N/A')}\n"
        f"📝 <b>Descripción:</b> {context.user_data.get('problema', '')[:200]}...\n\n"
        "<b>¿Confirmas que la información es correcta?</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Sí, crear ticket", callback_data="confirm_ticket")],
        [InlineKeyboardButton("❌ No, cancelar", callback_data="cancel_ticket")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(resumen, reply_markup=reply_markup)
    return CONFIRMING_TICKET

async def handle_ticket_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma o cancela la creación del ticket."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_ticket":
        ticket_id = save_ticket(context.user_data)
        if ticket_id:
            await query.edit_message_text(
                f"✅ <b>¡Ticket creado exitosamente!</b>\n\n"
                f"🎫 <b>Número de Ticket:</b> {ticket_id}\n"
                f"El equipo de TI ha sido notificado y se pondrá en contacto contigo.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ <b>Error al crear el ticket.</b>", parse_mode='HTML')
    else:
        await query.edit_message_text("❌ Creación de ticket cancelada.", parse_mode='HTML')

    # Limpiar datos temporales
    for key in ['categoria', 'categoria_key', 'subcategoria', 'problema']:
        if key in context.user_data:
            del context.user_data[key]
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¿En qué más puedo ayudarte?", reply_markup=main_markup)
    return SELECTING_ACTION

# --- Otras Funciones del Bot ---

async def view_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los tickets del usuario, priorizando los que están abiertos."""
    all_user_tickets = get_user_tickets(update.effective_user.id)
    
    if not all_user_tickets:
        await update.message.reply_text("📭 No tienes tickets de soporte registrados.", reply_markup=main_markup)
        return SELECTING_ACTION

    open_tickets = [t for t in all_user_tickets if t.get('estado', '').lower() == 'abierto']
    closed_tickets = [t for t in all_user_tickets if t.get('estado', '').lower() != 'abierto']
    
    response = ""
    
    if open_tickets:
        response += "📋 <b>Tus tickets de soporte ABIERTOS:</b>\n\n"
        for ticket in open_tickets[:5]:  # Mostrar máximo 5 tickets abiertos
            response += (
                f"🎫 <b>ID:</b> {ticket.get('id', 'N/A')}\n"
                f"📅 <b>Fecha:</b> {ticket.get('fecha', 'N/A')}\n"
                f"🏷️ <b>Asunto:</b> {ticket.get('subcategoria', 'N/A')}\n"
                f"🔰 <b>Estado:</b> {ticket.get('estado', 'Abierto')}\n"
                f"🚨 <b>Prioridad:</b> {ticket.get('prioridad', 'Media')}\n"
                "─" * 20 + "\n"
            )
        if len(open_tickets) > 5:
            response += f"\n📄 <i>Mostrando 5 de {len(open_tickets)} tickets abiertos.</i>\n\n"
    else:
        response += "✅ No tienes tickets abiertos en este momento.\n\n"

    if closed_tickets:
        response += "📜 <b>Historial de tus últimos tickets cerrados:</b>\n\n"
        for ticket in closed_tickets[:3]:  # Mostrar máximo 3 tickets cerrados
             response += (
                f"🎫 <b>ID:</b> {ticket.get('id', 'N/A')}\n"
                f"📅 <b>Fecha:</b> {ticket.get('fecha', 'N/A')}\n"
                f"🏷️ <b>Asunto:</b> {ticket.get('subcategoria', 'N/A')}\n"
                f"🔰 <b>Estado:</b> {ticket.get('estado', 'N/A')}\n"
                "─" * 20 + "\n"
            )

    await update.message.reply_html(response, reply_markup=main_markup)
    return SELECTING_ACTION

async def handle_policy_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las consultas de políticas basadas en el texto del teclado."""
    text_clean = ''.join(c for c in update.message.text.lower() if c.isalnum() or c.isspace()).strip()
    
    policy_map = {
        "ciberseguridad": "ciberseguridad", "respaldo": "respaldo",
        "mantenimiento": "mantenimiento", "control apps": "control aplicaciones",
        "licencias": "licencias", "antivirus": "antivirus",
        "credenciales": "credenciales", "acceso físico": "acceso fisico",
        "redes": "redes", "sistemas": "acceso sistemas",
        "correo": "correo", "internet": "internet",
        "clasificación": "clasificacion", "contraseñas": "contrasenas",
        "sanciones": "sanciones"
    }

    policy_key = next((value for key, value in policy_map.items() if key in text_clean), None)
            
    if policy_key and policy_key in POLITICAS:
        politica = POLITICAS[policy_key]
        respuesta = f"📜 <b>{politica['titulo']}</b>\n\n{politica['contenido']}"
        await update.message.reply_html(respuesta, reply_markup=politicas_markup)
    else:
        await update.message.reply_text("No he entendido tu solicitud. Usa los botones del menú.", reply_markup=main_markup)
    return SELECTING_ACTION

# --- COMANDOS DE ADMINISTRADOR ---

async def view_user_tickets_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para que un admin vea los tickets de un usuario específico."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Por favor, proporciona el ID del usuario.\n<b>Uso:</b> /ver_tickets [user_id]", parse_mode='HTML')
        return

    try:
        target_user_id = int(context.args[0])
    except (ValueError, IndexError):
        await update.message.reply_text("❌ ID de usuario no válido. Debe ser un número.")
        return

    tickets = get_user_tickets(target_user_id)
    if not tickets:
        await update.message.reply_text(f"📭 No se encontraron tickets para el usuario con ID: {target_user_id}")
        return

    open_tickets = [t for t in tickets if t.get('estado', '').lower() == 'abierto']
    closed_tickets = [t for t in tickets if t.get('estado', '').lower() != 'abierto']
    
    response = f"🔍 <b>Tickets para el usuario ID {target_user_id}:</b>\n\n"
    
    if open_tickets:
        response += "📋 <b>Tickets ABIERTOS:</b>\n\n"
        for ticket in open_tickets:
            response += (
                f"🎫 <b>ID:</b> {ticket.get('id', 'N/A')}\n"
                f"👤 <b>Reportado por:</b> {ticket.get('usuario', 'N/A')}\n"
                f"📅 <b>Fecha:</b> {ticket.get('fecha', 'N/A')}\n"
                f"🏷️ <b>Asunto:</b> {ticket.get('subcategoria', 'N/A')}\n"
                f"🔰 <b>Estado:</b> {ticket.get('estado', 'Abierto')}\n"
                "─" * 20 + "\n"
            )
    else:
        response += "✅ No hay tickets abiertos para este usuario.\n\n"

    if closed_tickets:
        response += "📜 <b>Historial de tickets cerrados:</b>\n\n"
        for ticket in closed_tickets[:5]:
             response += (
                f"🎫 <b>ID:</b> {ticket.get('id', 'N/A')}\n"
                f"👤 <b>Reportado por:</b> {ticket.get('usuario', 'N/A')}\n"
                f"📅 <b>Fecha:</b> {ticket.get('fecha', 'N/A')}\n"
                f"🔰 <b>Estado:</b> {ticket.get('estado', 'N/A')}\n"
                "─" * 20 + "\n"
            )

    await update.message.reply_html(response)

async def clean_duplicates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para limpiar duplicados del archivo CSV."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso para usar este comando.")
        return
    
    clean_csv_duplicates()
    await update.message.reply_text("✅ Limpieza de duplicados completada.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual y limpia los datos de la conversación."""
    for key in ['categoria', 'categoria_key', 'subcategoria', 'problema']:
        if key in context.user_data:
            del context.user_data[key]
            
    await update.message.reply_text("Operación cancelada. Volviendo al menú principal.", reply_markup=main_markup)
    return SELECTING_ACTION

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja errores inesperados."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ Ocurrió un error. Intenta de nuevo con /start.", reply_markup=main_markup)

# --- Punto de Entrada Principal ---

def main() -> None:
    """Función principal que configura e inicia el bot."""
    # Inicializar y limpiar el archivo de tickets
    init_tickets_file()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    main_menu_regex = r'^(🎫 Crear Ticket de Soporte|📋 Consultar Políticas|📊 Ver Mis Tickets|❓ Ayuda|🔙 Menú Principal)$'

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(main_menu_regex), handle_main_selection)
        ],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_selection)
            ],
            SELECTING_CATEGORY: [
                CallbackQueryHandler(handle_category_selection)
            ],
            SELECTING_SUBCATEGORY: [
                CallbackQueryHandler(handle_subcategory_selection)
            ],
            DESCRIBING_ISSUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_problem_description)
            ],
            CONFIRMING_TICKET: [
                CallbackQueryHandler(handle_ticket_confirmation)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ver_tickets", view_user_tickets_admin))
    application.add_handler(CommandHandler("limpiar_duplicados", clean_duplicates_command))
    application.add_error_handler(error_handler)

    logger.info("Iniciando bot...")
    application.run_polling()

if __name__ == '__main__':
    main()