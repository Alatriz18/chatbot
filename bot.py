import logging
import json
import psycopg2
import datetime
import os
import asyncio
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackQueryHandler, ConversationHandler
)

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Constantes y Configuración ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7375336597:AAFL8wRI0462-lXECPNFQSoI2kZNbWLMphg")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "https://webhookbot.c-toss.com/api/bot/webhooks/92929b3f-bad4-47df-9f7b-48dc6a1b9b61")
KNOWLEDGE_BASE_FILE = 'knowledge_base.json'
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345Prove@172.20.4.61:5432/postgres")
ADMIN_CHAT_IDS = [1510724514, 1147341167, 8278666256]  # ¡CORREGIDO! Múltiples IDs van en la misma lista, separados por coma.

# --- Estados de la Conversación ---
(
    SELECTING_ACTION, SELECTING_CATEGORY, SELECTING_SUBCATEGORY,
    CONFIRMING_ESCALATION, DESCRIBING_ISSUE, CONFIRMING_TICKET,
    SELECTING_POLICY, VIEWING_TICKETS, ADMIN_PANEL
) = range(9)

# --- Carga de la Base de Conocimiento ---
try:
    with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
        KNOWLEDGE_BASE = json.load(f)
except Exception as e:
    logger.error(f"Error fatal al cargar la base de conocimiento '{KNOWLEDGE_BASE_FILE}': {e}")
    exit()

# --- Funciones de Base de Datos ---
def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError as e:
        logger.error(f"No se pudo conectar a la base de datos: {e}")
        return None

def save_ticket_to_db(user_data: dict) -> str | None:
    conn = get_db_connection()
    if not conn: return None
    ticket_id_str = f"TKT-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    categoria_key = user_data.get('categoria_key', '')
    tipo_ticket = 'Software' if 'software' in categoria_key.lower() else 'Hardware'
    sql = """
        INSERT INTO soporte_ti.stticket 
        (ticket_des_ticket, ticket_id_ticket, ticket_tip_ticket, ticket_est_ticket, 
         ticket_idt_ticket, ticket_asu_ticket, ticket_tusua_ticket)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                user_data.get('problema', 'N/A'),
                ticket_id_str, tipo_ticket, 'PE',
                user_data.get('user_id', None),
                user_data.get('subcategoria_titulo', 'Sin asunto'),
                user_data.get('username', 'N/A')
            ))
            conn.commit()
        logger.info(f"Ticket {ticket_id_str} guardado en la base de datos.")
        return ticket_id_str
    except Exception as e:
        logger.error(f"Error al guardar ticket en la base de datos: {e}")
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def get_user_tickets_from_db(user_id: int) -> list:
    conn = get_db_connection()
    if not conn: return []
    sql = """
        SELECT ticket_id_ticket, ticket_asu_ticket, ticket_est_ticket
        FROM soporte_ti.stticket
        WHERE ticket_idt_ticket = %s ORDER BY ticket_fec_ticket DESC;
    """
    tickets = []
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            for row in cur.fetchall():
                tickets.append({'id': row[0], 'asunto': row[1], 'estado': row[2]})
        return tickets
    except Exception as e:
        logger.error(f"Error al obtener tickets de usuario: {e}")
        return []
    finally:
        if conn: conn.close()

def get_single_ticket_from_db(ticket_id: str, user_id: int) -> dict | None:
    conn = get_db_connection()
    if not conn: return None
    sql = """
        SELECT ticket_id_ticket, ticket_fec_ticket, ticket_asu_ticket, 
               ticket_est_ticket, ticket_des_ticket, ticket_urg_ticket
        FROM soporte_ti.stticket
        WHERE ticket_id_ticket = %s AND ticket_idt_ticket = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (ticket_id, user_id))
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0], 'fecha': row[1].strftime('%Y-%m-%d %H:%M'), 'asunto': row[2],
                    'estado': row[3], 'descripcion': row[4], 'urgencia': row[5]
                }
            return None
    finally:
        if conn: conn.close()

def get_all_tickets_from_db() -> list:
    conn = get_db_connection()
    if not conn: return []
    sql = """
        SELECT ticket_id_ticket, ticket_fec_ticket, ticket_asu_ticket, ticket_est_ticket, ticket_tusua_ticket
        FROM soporte_ti.stticket ORDER BY ticket_fec_ticket DESC;
    """
    tickets = []
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            for row in cur.fetchall():
                tickets.append({
                    'id': row[0], 'fecha': row[1].strftime('%Y-%m-%d %H:%M'), 'asunto': row[2],
                    'estado': row[3], 'usuario': row[4]
                })
        return tickets
    finally:
        if conn: conn.close()

def update_ticket_status_in_db(ticket_id: str, new_status: str) -> bool:
    """Actualiza el estado de un ticket específico."""
    conn = get_db_connection()
    if not conn: return False
    sql = "UPDATE soporte_ti.stticket SET ticket_est_ticket = %s WHERE ticket_id_ticket = %s;"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (new_status, ticket_id))
            conn.commit()
        logger.info(f"Estado del ticket {ticket_id} actualizado a {new_status}.")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar estado del ticket {ticket_id}: {e}")
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def get_single_ticket_for_admin_from_db(ticket_id: str) -> dict | None:
    """Obtiene detalles de cualquier ticket para un admin (sin verificar user_id)."""
    conn = get_db_connection()
    if not conn: return None
    sql = """
        SELECT t.ticket_id_ticket, t.ticket_fec_ticket, t.ticket_asu_ticket, t.ticket_est_ticket, 
               t.ticket_des_ticket, t.ticket_urg_ticket, t.ticket_tusua_ticket
        FROM soporte_ti.stticket t
        WHERE t.ticket_id_ticket = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (ticket_id,))
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0], 'fecha': row[1].strftime('%Y-%m-%d %H:%M'), 'asunto': row[2],
                    'estado': row[3], 'descripcion': row[4], 'urgencia': row[5], 'usuario': row[6]
                }
            return None
    finally:
        if conn: conn.close()

# --- Funciones de Notificación ---
async def send_teams_notification(ticket_id: str, user_data: dict):
    if not TEAMS_WEBHOOK_URL or not TEAMS_WEBHOOK_URL.startswith("http"):
        logger.warning("La URL del webhook no está configurada.")
        return
    def sanitize(text: str) -> str:
        return text.strip()[:1024] if isinstance(text, str) else "N/A"
    
    username = sanitize(user_data.get('username', 'N/A'))
    subcategoria = sanitize(user_data.get('subcategoria_titulo', 'N/A'))
    descripcion = sanitize(user_data.get('problema', 'N/A'))
    fecha_str = datetime.datetime.now().strftime('%Y-%m-%d a las %H:%M:%S')
    texto_principal = (
        f"El usuario '{username}' ha generado un ticket sobre '{subcategoria}' con fecha {fecha_str}.\n\n"
        f"**Descripción del usuario:** \"{descripcion}\""
    )
    payload = {
        "type": "message", "text": texto_principal,
        "attachments": [{"color": "#0076D7", "title": f"Detalles Técnicos del Ticket: {ticket_id}"}]
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(TEAMS_WEBHOOK_URL, json=payload, timeout=10)
        logger.info(f"Notificación del ticket {ticket_id} enviada.")
    except Exception as e:
        logger.error(f"Error al enviar notificación: {e}")

# --- Flujo Principal y Menús ---
async def get_main_menu_keyboard(update: Update) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🛎️ Reportar un Problema", callback_data="report_problem")],
        [InlineKeyboardButton("📋 Consultar Políticas", callback_data="consult_policies")],
        [InlineKeyboardButton("📊 Ver Mis Tickets", callback_data="view_tickets")],
    ]
    if update.effective_user.id in ADMIN_CHAT_IDS:
        keyboard.append([InlineKeyboardButton("👑 Panel de Administrador", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str = None):
    user = update.effective_user
    message_text = message or rf"👋 ¡Hola {user.mention_html()}! ¿Cómo puedo ayudarte?"
    reply_markup = await get_main_menu_keyboard(update)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_html(text=message_text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data['username'] = update.effective_user.full_name
    context.user_data['user_id'] = update.effective_user.id
    await show_main_menu(update, context)
    return SELECTING_ACTION

# --- Flujo de Creación de Tickets ---
async def start_troubleshooting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    categorias = [[InlineKeyboardButton(v['titulo'], callback_data=k)] for k, v in KNOWLEDGE_BASE.get('casos_soporte', {}).items()]
    categorias.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data="back_to_main_menu")])
    await query.edit_message_text(
        text="Ok, empecemos. <b>¿Qué tipo de problema tienes?</b>",
        reply_markup=InlineKeyboardMarkup(categorias), parse_mode='HTML'
    )
    return SELECTING_CATEGORY
    
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    categoria_key = query.data
    context.user_data['categoria_key'] = categoria_key
    context.user_data['categoria_titulo'] = KNOWLEDGE_BASE['casos_soporte'][categoria_key]['titulo']
    casos = KNOWLEDGE_BASE['casos_soporte'][categoria_key]['categorias']
    subcategorias = [[InlineKeyboardButton(v['titulo'], callback_data=k)] for k, v in casos.items()]
    subcategorias.append([InlineKeyboardButton("🔙 Volver a Categorías", callback_data="back_to_categories")])
    await query.edit_message_text(
        "Entendido. <b>Ahora, sé más específico:</b>",
        reply_markup=InlineKeyboardMarkup(subcategorias), parse_mode='HTML'
    )
    return SELECTING_SUBCATEGORY

async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    subcategoria_key = query.data
    categoria_key = context.user_data['categoria_key']
    context.user_data['subcategoria_key'] = subcategoria_key
    solucion_data = KNOWLEDGE_BASE['casos_soporte'][categoria_key]['categorias'][subcategoria_key]
    context.user_data['subcategoria_titulo'] = solucion_data['titulo']
    pasos_texto = "\n".join(solucion_data['pasos'])
    mensaje = (
        f"Ok: <b>'{solucion_data['titulo']}'</b>\n\nPor favor, intenta estos pasos:\n\n{pasos_texto}\n\n"
        f"--------------------\n<b>{solucion_data['titulo_confirmacion']}</b>"
    )
    keyboard = [[
        InlineKeyboardButton("❌ No, necesito ayuda", callback_data="escalate"),
        InlineKeyboardButton("✅ Sí, se solucionó", callback_data="solved")
    ]]
    await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return CONFIRMING_ESCALATION

async def handle_escalation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "solved":
        await query.edit_message_text("¡Excelente! Me alegra haberte ayudado. 👍")
        await asyncio.sleep(2)
        return await start(update, context)
    elif query.data == "escalate":
        await query.edit_message_text(
            "Entendido. Para crear el ticket, <b>describe tu problema con detalle.</b>",
            parse_mode='HTML'
        )
        return DESCRIBING_ISSUE
    return CONFIRMING_ESCALATION

async def handle_problem_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['problema'] = update.message.text
    resumen = (
        "📋 <b>Resumen del Ticket a Crear:</b>\n\n"
        f"🏷️ <b>Categoría:</b> {context.user_data.get('categoria_titulo', 'N/A')}\n"
        f"🔍 <b>Problema:</b> {context.user_data.get('subcategoria_titulo', 'N/A')}\n"
        f"📝 <b>Detalles:</b> {context.user_data.get('problema', '')[:200]}...\n\n"
        "<b>¿Confirmas la creación del ticket?</b>"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Sí, crear", callback_data="confirm_ticket"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancel_ticket")
    ]]
    await update.message.reply_html(resumen, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMING_TICKET

async def handle_ticket_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_ticket":
        await query.edit_message_text(text="⏳ Generando tu ticket, por favor espera...", parse_mode='HTML')
        ticket_id = save_ticket_to_db(context.user_data)
        if ticket_id:
            await send_teams_notification(ticket_id, context.user_data)
            await query.edit_message_text(
                text=(f"✅ <b>¡Ticket creado con éxito!</b>\n\n🎫 <b>Tu número de ticket es:</b> {ticket_id}"),
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(text="❌ Hubo un error al guardar tu ticket.", parse_mode='HTML')
    else:
        await query.edit_message_text("❌ Creación de ticket cancelada.")
    await asyncio.sleep(4)
    return await start(update, context)

# --- Flujo de Consulta de Tickets de Usuario ---
async def view_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    all_tickets = get_user_tickets_from_db(update.effective_user.id)
    if not all_tickets:
        await query.answer("No tienes tickets registrados.", show_alert=True)
        return VIEWING_TICKETS
    keyboard = []
    for ticket in all_tickets:
        status_emoji = "🟢" if ticket.get('estado') == 'FN' else "🟡"
        keyboard.append([InlineKeyboardButton(
            f"{status_emoji} {ticket.get('id')} - {ticket.get('asunto', 'N/A')}",
            callback_data=f"view_ticket_{ticket.get('id')}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data="back_to_main_menu")])
    await query.edit_message_text(
        text="📋 *Tus Tickets de Soporte*\n\nSelecciona un ticket para ver sus detalles:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )
    return VIEWING_TICKETS

async def show_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    ticket_id = query.data.split('_')[-1]
    ticket = get_single_ticket_from_db(ticket_id, update.effective_user.id)
    if not ticket:
        await query.edit_message_text(text="❌ Error: No se encontró el ticket.")
        return VIEWING_TICKETS
    status_emoji = "🟢" if ticket.get('estado') == 'FN' else "🟡"
    message_text = (
        f"📄 *Detalles del Ticket {ticket.get('id')}*\n\n"
        f"*{status_emoji} Estado:* {ticket.get('estado', 'N/A')}\n"
        f"*📅 Fecha:* {ticket.get('fecha', 'N/A')}\n"
        f"*🏷️ Asunto:* {ticket.get('asunto', 'N/A')}\n"
        f"* Urgencia:* {ticket.get('urgencia', 'N/A')}\n\n"
        f"*📝 Descripción:*\n{ticket.get('descripcion', 'N/A')}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver a la lista", callback_data="back_to_ticket_list")]]
    await query.edit_message_text(text=message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return VIEWING_TICKETS
    
# --- Flujo de Políticas ---
async def show_policy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    politicas_keys = [k for k in KNOWLEDGE_BASE.keys() if k not in ['casos_soporte']]
    keyboard = [[InlineKeyboardButton(KNOWLEDGE_BASE[key].get('titulo', key), callback_data=key)] for key in sorted(politicas_keys)]
    keyboard.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data="back_to_main_menu")])
    await query.edit_message_text("📚 <b>Selecciona la política a consultar:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return SELECTING_POLICY

async def handle_policy_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    policy_key = query.data
    selected_policy = KNOWLEDGE_BASE.get(policy_key)
    respuesta = f"📜 <b>{selected_policy['titulo']}</b>\n\n{selected_policy['contenido']}"
    keyboard = [[InlineKeyboardButton("🔙 Volver a Políticas", callback_data="show_policy_menu")]]
    await query.edit_message_text(text=respuesta, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return SELECTING_POLICY

# --- Flujo de Administrador ---
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📊 Ver y Gestionar Tickets", callback_data="admin_view_all_tickets_page_0")],
        [InlineKeyboardButton("🔙 Volver al Menú Principal", callback_data="back_to_main_menu")]
    ]
    await query.edit_message_text(
        text="👑 *Panel de Administrador*\n\nSelecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )
    return ADMIN_PANEL

# --- Flujo de Administrador (VERSIÓN CORREGIDA Y MEJORADA) ---

def get_admin_ticket_list_content(page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    """
    NUEVA FUNCIÓN AUXILIAR: Genera el texto y los botones para la lista de tickets.
    Es reutilizable y mantiene el código limpio.
    """
    tickets_per_page = 5
    all_tickets = get_all_tickets_from_db()
    
    if not all_tickets:
        text = "No hay tickets registrados en el sistema."
        keyboard = [[InlineKeyboardButton("🔙 Volver al Panel", callback_data="admin_panel")]]
        return text, InlineKeyboardMarkup(keyboard)

    start_index = page * tickets_per_page
    end_index = start_index + tickets_per_page
    tickets_to_show = all_tickets[start_index:end_index]

    # Mensaje de cabecera
    text = f"📊 *Gestión de Tickets (Página {page + 1})*\n\n"
    keyboard = []
    
    # Construcción de la lista de tickets
    for ticket in tickets_to_show:
        status_emoji = "🟢" if ticket.get('estado') == 'FN' else "🟡"
        user_name = (ticket.get('usuario', 'N/A') or 'N/A').replace("_", " ").title()[:20]
        ticket_id = ticket.get('id')
        
        text += f"{status_emoji} `{ticket_id}` - *De:* {user_name}\n"

        buttons = [InlineKeyboardButton("👁️ Ver Detalles", callback_data=f"admin_view_ticket_{ticket_id}")]
        if ticket.get('estado') != 'FN':
            buttons.append(InlineKeyboardButton("✅ Cerrar Ticket", callback_data=f"admin_close_ticket_{ticket_id}_{page}")) # Añadimos la página actual
        keyboard.append(buttons)
        
    # Botones de navegación (paginación)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"admin_view_all_tickets_page_{page - 1}"))
    if end_index < len(all_tickets):
        nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"admin_view_all_tickets_page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton("🔙 Volver al Panel", callback_data="admin_panel")])
    
    return text, InlineKeyboardMarkup(keyboard)


async def admin_view_all_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """FUNCIÓN ACTUALIZADA: Ahora solo llama a la función auxiliar para mostrar el menú."""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split('_')[-1])
    text, reply_markup = get_admin_ticket_list_content(page=page)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ADMIN_PANEL


async def admin_show_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Esta función no necesita cambios, pero se incluye para que copies el bloque completo."""
    query = update.callback_query
    await query.answer()
    ticket_id = query.data.split('_')[-1]
    ticket = get_single_ticket_for_admin_from_db(ticket_id)
    if not ticket:
        await query.answer("No se pudo encontrar el ticket.", show_alert=True)
        return ADMIN_PANEL
    
    status_emoji = "🟢" if ticket.get('estado') == 'FN' else "🟡"
    message_text = (
        f"📄 *Detalles del Ticket {ticket.get('id')}* (Admin View)\n\n"
        f"*{status_emoji} Estado:* {ticket.get('estado')}\n"
        f"*👤 Usuario:* {ticket.get('usuario')}\n"
        f"*📅 Fecha:* {ticket.get('fecha')}\n"
        f"*🏷️ Asunto:* {ticket.get('asunto')}\n"
        f"* Urgencia:* {ticket.get('urgencia')}\n\n"
        f"*📝 Descripción:*\n{ticket.get('descripcion')}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Volver a la lista de Tickets", callback_data="admin_view_all_tickets_page_0")]]
    await query.edit_message_text(text=message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ADMIN_PANEL


async def admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """FUNCIÓN CORREGIDA: Cierra el ticket y actualiza el menú al instante."""
    query = update.callback_query
    
    # Extraemos el ID del ticket y la página actual
    parts = query.data.split('_')
    ticket_id = parts[3]
    current_page = int(parts[4])

    success = update_ticket_status_in_db(ticket_id, 'FN')
    if success:
        await query.answer(f"✅ Ticket {ticket_id} cerrado con éxito.", show_alert=False) # Usamos una notificación sutil
    else:
        await query.answer(f"❌ Error al cerrar el ticket {ticket_id}.", show_alert=True)
        return ADMIN_PANEL # Si hay error, no hacemos nada más
    
    # ¡AQUÍ ESTÁ LA MAGIA!
    # 1. Obtenemos el contenido actualizado de la lista de tickets.
    text, reply_markup = get_admin_ticket_list_content(page=current_page)
    
    # 2. Editamos el mensaje actual para reflejar el cambio.
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return ADMIN_PANEL

# --- Función Principal ---
def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(start_troubleshooting, pattern=r'^report_problem$'),
                CallbackQueryHandler(show_policy_menu, pattern=r'^consult_policies$'),
                CallbackQueryHandler(view_my_tickets, pattern=r'^view_tickets$'),
                CallbackQueryHandler(show_admin_panel, pattern=r'^admin_panel$'),
            ],
            SELECTING_CATEGORY: [
                CallbackQueryHandler(start, pattern=r'^back_to_main_menu$'),
                CallbackQueryHandler(handle_category_selection)
            ],
            SELECTING_SUBCATEGORY: [
                CallbackQueryHandler(start_troubleshooting, pattern=r'^back_to_categories$'),
                CallbackQueryHandler(handle_subcategory_selection)
            ],
            CONFIRMING_ESCALATION: [CallbackQueryHandler(handle_escalation_confirmation)],
            DESCRIBING_ISSUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_problem_description)],
            CONFIRMING_TICKET: [CallbackQueryHandler(handle_ticket_confirmation)],
            SELECTING_POLICY: [
                CallbackQueryHandler(start, pattern=r'^back_to_main_menu$'),
                CallbackQueryHandler(show_policy_menu, pattern=r'^show_policy_menu$'),
                CallbackQueryHandler(handle_policy_selection)
            ],
            VIEWING_TICKETS: [
                CallbackQueryHandler(show_ticket_details, pattern=r'^view_ticket_'),
                CallbackQueryHandler(view_my_tickets, pattern=r'^back_to_ticket_list$'),
                CallbackQueryHandler(start, pattern=r'^back_to_main_menu$'),
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(admin_view_all_tickets, pattern=r'^admin_view_all_tickets_page_'),
                CallbackQueryHandler(admin_show_ticket_details, pattern=r'^admin_view_ticket_'),
                CallbackQueryHandler(admin_close_ticket, pattern=r'^admin_close_ticket_'),
                CallbackQueryHandler(show_admin_panel, pattern=r'^admin_panel$'),
                CallbackQueryHandler(start, pattern=r'^back_to_main_menu$'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', start), 
            CommandHandler("start", start),
        ],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    logger.info("Iniciando bot...")
    application.run_polling()

if __name__ == '__main__':
    main()

