document.addEventListener('DOMContentLoaded', async () => {
    // --- CONFIGURACIÓN USANDO CONFIG CENTRALIZADO ---
    const API_BASE_URL = window.APP_CONFIG.getApiUrl();
    
    console.log('🌐 Configuración de red detectada:');
    console.log('Hostname:', window.location.hostname);
    console.log('API URL:', API_BASE_URL);
    let KNOWLEDGE_BASE = {};
    let state = {
        current: 'SELECTING_ACTION',
        context: {
            attachedFiles: [] //  NUEVO: Array para archivos durante la descripción
        }
    };
    const loggedInUser = JSON.parse(sessionStorage.getItem('user'));
    const sessionId = `${loggedInUser.username}-${Date.now()}`;

    // --- ELEMENTOS DEL DOM ---
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const fileInput = document.getElementById('fileInput');
    const attachButton = document.getElementById('attachButton');

    // --- INICIALIZACIÓN DEL SISTEMA DE ARCHIVOS ---
    setupFileUpload();

    // --- FUNCIÓN DE LOGGING ---
    async function logInteraction(logData) {
        try {
            await fetch(`${API_BASE_URL}/log/interaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sessionId: sessionId,
                    username: loggedInUser.username,
                    actionType: logData.actionType,
                    actionValue: logData.actionValue,
                    botResponse: logData.botResponse || ''
                })
            });
        } catch (error) {
            console.error('Error al registrar la interacción:', error);
        }
    }
     // --- VERIFICACIÓN DE ROL Y BOTÓN ADMIN ---
    function checkAdminRoleAndSetup() {
        if (loggedInUser && loggedInUser.rol === 'admin') {
            // Crear botón de administración si no existe
            let adminButton = document.getElementById('adminPanelButton');
            if (!adminButton) {
                adminButton = document.createElement('button');
                adminButton.id = 'adminPanelButton';
                adminButton.className = 'admin-panel-btn';
                adminButton.innerHTML = '<i class="fas fa-cog"></i> Panel Admin';
                adminButton.title = 'Ir al Panel de Administración';
                
                // Estilos inline para el botón
                adminButton.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 10px 15px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 25px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    transition: all 0.3s ease;
                `;
                
                // Efectos hover
                adminButton.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.4)';
                });
                
                adminButton.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.3)';
                });
                
                // Evento click para redirigir
                adminButton.addEventListener('click', function() {
                    // Registrar la acción en logs
                    logInteraction({
                        actionType: 'navegacion_admin',
                        actionValue: 'click_panel_admin'
                    });
                    
                    // Redirigir al panel de administración
                    window.location.href = 'admin.html';
                });
                
                document.body.appendChild(adminButton);
            }
            
            // También agregar opción en el menú principal para admins
            setTimeout(() => {
                addAdminOptionToMenu();
            }, 1000);
        }
    }
    
    function addAdminOptionToMenu() {
        // Verificar si ya existe la opción admin en el menú
        const existingAdminOption = document.querySelector('[data-action="go_to_admin"]');
        if (!existingAdminOption) {
            // Agregar opción de admin al menú principal
            const lastMessage = chatMessages.querySelector('.message:last-child');
            if (lastMessage && lastMessage.querySelector('.message-buttons')) {
                const buttonsContainer = lastMessage.querySelector('.message-buttons');
                const adminButton = document.createElement('button');
                adminButton.className = 'message-btn';
                adminButton.dataset.action = 'go_to_admin';
                adminButton.innerHTML = '⚙️ Panel de Administración';
                buttonsContainer.appendChild(adminButton);
            }
        }
    }

    // --- INICIALIZACIÓN ---
    try {
        const response = await fetch('knowledge_base.json');
        KNOWLEDGE_BASE = await response.json();
        startChat();
    } catch (error) {
        console.error("Error al cargar la base de conocimiento:", error);
        addMessage({ text: "Lo siento, hay un error crítico y no puedo iniciar. Por favor, contacta a soporte." });
    }

    function startChat() {
        const welcomeMessage = `¡Hola, <strong>${loggedInUser.username}</strong>! 👋 Soy tu asistente virtual de TI. ¿Cómo puedo ayudarte hoy?`;
        addMessage({ text: welcomeMessage });
        displayMainMenu();
    }

    // --- SISTEMA DE ARCHIVOS ADJUNTOS MEJORADO ---
    function setupFileUpload() {
        // Ocultar botón inicialmente
        attachButton.style.display = 'none';
        
        attachButton.addEventListener('click', () => {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', handleFileSelection);
        
        //  NUEVO: Permitir pegar imágenes con Ctrl+V durante la descripción
        userInput.addEventListener('paste', handlePasteImage);
    }

    function handlePasteImage(e) {
        // Solo procesar si estamos en modo de descripción
        if (state.current !== 'DESCRIBING_ISSUE') return;
        
        const items = e.clipboardData?.items;
        if (!items) return;
        
        for (let item of items) {
            if (item.type.indexOf('image') !== -1) {
                e.preventDefault();
                const file = item.getAsFile();
                if (file) {
                    // Validar el archivo
                    if (!allowedFile(file.name)) {
                        showTempMessage('❌ Solo se permiten imágenes (PNG, JPG, GIF) al pegar', 'error');
                        return;
                    }
                    if (file.size > (16 * 1024 * 1024)) {
                        showTempMessage('❌ La imagen es demasiado grande (máximo 16MB)', 'error');
                        return;
                    }
                    
                    // Agregar al contexto
                    state.context.attachedFiles.push(file);
                    showFilePreview();
                    showTempMessage('✅ Imagen pegada correctamente. Puedes agregar más archivos con el clip.', 'success');
                }
                break;
            }
        }
    }

    //  CORREGIDO: Permitir más tipos de archivos
    function allowedFile(filename) {
        const allowedExtensions = [
            'png', 'jpg', 'jpeg', 'gif', // Imágenes
            'pdf', // PDF
            'doc', 'docx', // Word
            'xls', 'xlsx', // Excel
            'txt', // Texto
            'zip', 'rar' // Comprimidos
        ];
        const extension = filename.split('.').pop().toLowerCase();
        return allowedExtensions.includes(extension);
    }

    function showTempMessage(message, type) {
        const tempMsg = document.createElement('div');
        tempMsg.className = `temp-message ${type}`;
        tempMsg.textContent = message;
        tempMsg.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 5px;
            color: white;
            z-index: 1000;
            font-size: 14px;
            background: ${type === 'error' ? '#ef4444' : '#10b981'};
        `;
        document.body.appendChild(tempMsg);
        
        setTimeout(() => {
            if (document.contains(tempMsg)) {
                tempMsg.remove();
            }
        }, 3000);
    }

    function handleFileSelection(event) {
        const files = event.target.files;
        if (files.length === 0) return;
        
        //  MODIFICADO: Solo permitir durante la descripción del problema
        if (state.current !== 'DESCRIBING_ISSUE') {
            showTempMessage('⚠️ Solo puedes adjuntar archivos cuando estés describiendo el problema', 'error');
            fileInput.value = '';
            return;
        }
        
        // Validar archivos
        const validFiles = Array.from(files).filter(file => {
            if (!allowedFile(file.name)) {
                showTempMessage(`❌ "${file.name}" no es un tipo de archivo permitido`, 'error');
                return false;
            }
            if (file.size > (16 * 1024 * 1024)) {
                showTempMessage(`❌ "${file.name}" es demasiado grande (máximo 16MB)`, 'error');
                return false;
            }
            return true;
        });
        
        if (validFiles.length === 0) {
            fileInput.value = '';
            return;
        }
        
        // Agregar archivos al contexto
        validFiles.forEach(file => {
            state.context.attachedFiles.push(file);
        });
        
        showFilePreview();
        fileInput.value = '';
    }

    function showFilePreview() {
        // Remover preview anterior si existe
        const existingPreview = document.getElementById('filePreview');
        if (existingPreview) existingPreview.remove();
        
        const files = state.context.attachedFiles;
        if (files.length === 0) return;
        
        const previewContainer = document.createElement('div');
        previewContainer.id = 'filePreview';
        previewContainer.className = 'file-preview';
        
        previewContainer.innerHTML = `
            <div class="file-preview-header">
                <h4>📎 Archivos adjuntos (${files.length})</h4>
                <button class="close-preview" id="closePreview">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="files-list" id="filesList"></div>
            <div class="file-actions">
                <button class="btn-secondary" id="addMoreFiles">
                    <i class="fas fa-plus"></i> Agregar más archivos
                </button>
                <span class="file-count">${files.length} archivo(s) listo(s) para enviar con el ticket</span>
            </div>
        `;
        
        const filesList = previewContainer.querySelector('#filesList');
        
        files.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-icon">
                    <i class="fas fa-${getFileIcon(file.name)}"></i>
                </div>
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <button class="remove-file" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            filesList.appendChild(fileItem);
        });
        
        // Insertar después del área de chat
        chatMessages.parentNode.insertBefore(previewContainer, chatMessages.nextSibling);
        
        // Event listeners
        previewContainer.querySelector('#closePreview').addEventListener('click', () => {
            previewContainer.remove();
        });
        
        previewContainer.querySelector('#addMoreFiles').addEventListener('click', () => {
            fileInput.click();
        });
        
        // Agregar event listeners para eliminar archivos individuales
        previewContainer.querySelectorAll('.remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                removeFileFromPreview(index);
            });
        });
    }

    function removeFileFromPreview(index) {
        state.context.attachedFiles.splice(index, 1);
        
        // Actualizar preview o removerlo si no hay archivos
        if (state.context.attachedFiles.length === 0) {
            const previewContainer = document.getElementById('filePreview');
            if (previewContainer) previewContainer.remove();
        } else {
            showFilePreview(); // Recargar preview
        }
    }

    function getFileIcon(filename) {
        const extension = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': 'file-pdf',
            'doc': 'file-word',
            'docx': 'file-word',
            'xls': 'file-excel',
            'xlsx': 'file-excel',
            'jpg': 'file-image',
            'jpeg': 'file-image',
            'png': 'file-image',
            'gif': 'file-image',
            'zip': 'file-archive',
            'rar': 'file-archive',
            'txt': 'file-alt'
        };
        return icons[extension] || 'file';
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // --- FUNCIONES DEL CHAT CORREGIDAS ---
    function addMessage({ text, buttons = [] }, sender = 'bot') {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) typingIndicator.remove();

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        const avatar = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        const buttonsHTML = buttons.map(btn => 
            `<button class="message-btn" data-action="${btn.action}">${btn.text}</button>`
        ).join('');

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${text.replace(/\n/g, '<br>')}</div>
                ${buttonsHTML ? `<div class="message-buttons">${buttonsHTML}</div>` : ''}
            </div>`;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.id = 'typing-indicator';
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-text typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- LÓGICA DE CONVERSACIÓN MODIFICADA ---
    function handleAction(action) {
        const lastMessageButtons = chatMessages.querySelectorAll('.message:last-child .message-btn');
        lastMessageButtons.forEach(btn => btn.disabled = true);
        
        const [type, ...params] = action.split(':');
        
        const clickedButton = document.querySelector(`button[data-action="${action}"]`);
        if (clickedButton) {
            addMessage({ text: clickedButton.innerText }, 'user');
        }
        
        logInteraction({
            actionType: 'click_boton',
            actionValue: action
        });

        showTypingIndicator();

        setTimeout(() => {
            switch (state.current) {
                case 'SELECTING_ACTION':
                    handleMainMenuSelection(type);
                    break;
                case 'SELECTING_CATEGORY':
                    handleCategorySelection(type, params);
                    break;
                case 'SELECTING_SUBCATEGORY':
                    handleSubcategorySelection(type, params);
                    break;
                case 'CONFIRMING_ESCALATION':
                    handleEscalationConfirmation(type);
                    break;
                case 'ASKING_FINAL_OPTIONS':
                    const optionIndex = parseInt(params[0], 10);
                    const categoryKey = state.context.categoryKey;
                    const subcategoryKey = state.context.subcategoryKey;
                    const solution = KNOWLEDGE_BASE.casos_soporte[categoryKey].categorias[subcategoryKey];
                    const optionTitle = solution.opciones_finales[optionIndex].titulo;
                    if (type === 'final_option_solved') {
                        handleEscalationConfirmation('solved');
                    } else if (type === 'final_option_failed') {
                        state.context.finalOptionsTried.push(optionTitle);
                        state.context.finalOptionIndex++;
                        askFinalOption(state.context.finalOptionIndex);
                    }
                    break;
                case 'SELECTING_PREFERENCE':
                    const preference = params[0] === 'none' ? null : params[0];
                    //  CORREGIDO: Ahora crear ticket con archivos si existen
                    createTicketWithAttachments(preference);
                    break;
                case 'SELECTING_POLICY':
                    if (type === 'main_menu') displayMainMenu();
                    else handlePolicySelection(params[0]);
                    break;
            }
        }, 800);
    }

    function displayMainMenu() {
        state.current = 'SELECTING_ACTION';
        state.context = {
            attachedFiles: [] // Limpiar archivos al volver al menú
        };
        
        // Ocultar botón de adjuntar
        attachButton.style.display = 'none';
        
        // Limpiar preview si existe
        const previewContainer = document.getElementById('filePreview');
        if (previewContainer) previewContainer.remove();
        
        addMessage({
            text: "¿Qué necesitas hacer?",
            buttons: [
                { text: "🛎️ Reportar un Problema", action: "report_problem" },
                { text: "📋 Consultar Políticas", action: "consult_policies" }
            ]
        });
    }
     if (loggedInUser && loggedInUser.rol === 'admin') {
            menuButtons.push({ text: "⚙️ Panel de Administración", action: "go_to_admin" });
        }

    function handleMainMenuSelection(selection) {
        if (selection === 'report_problem') {
            state.current = 'SELECTING_CATEGORY';
            const categories = Object.keys(KNOWLEDGE_BASE.casos_soporte).map(key => ({
                text: KNOWLEDGE_BASE.casos_soporte[key].titulo,
                action: `category:${key}`
            }));
            categories.push({ text: "🔙 Volver al Menú", action: "main_menu" });
            addMessage({ text: "Entendido. ¿Qué tipo de problema tienes?", buttons: categories });
        } else if (selection === 'consult_policies') {
            state.current = 'SELECTING_POLICY';
            const policies = Object.keys(KNOWLEDGE_BASE.politicas).map(key => ({
                text: KNOWLEDGE_BASE.politicas[key].titulo,
                action: `policy:${key}`
            }));
            policies.push({ text: "🔙 Volver al Menú", action: "main_menu" });
            addMessage({ text: "Claro, aquí están las políticas. ¿Cuál deseas consultar?", buttons: policies });
        }
    }
    
    function handlePolicySelection(policyKey) {
        const policy = KNOWLEDGE_BASE.politicas[policyKey];
        //  CORREGIDO: Usar innerHTML para respetar saltos de línea
        addMessage({ text: `<strong>${policy.titulo}</strong><br><br>${policy.contenido.replace(/\n/g, '<br>')}` });
        setTimeout(displayMainMenu, 2000);
    }

    function handleCategorySelection(type, params) {
        if (type === 'main_menu') {
            displayMainMenu();
            return;
        }
        const categoryKey = params[0];
        state.context.categoryKey = categoryKey;
        state.current = 'SELECTING_SUBCATEGORY';

        const subcategories = Object.keys(KNOWLEDGE_BASE.casos_soporte[categoryKey].categorias).map(key => ({
            text: KNOWLEDGE_BASE.casos_soporte[categoryKey].categorias[key].titulo,
            action: `subcategory:${key}`
        }));
        subcategories.push({ text: "🔙 Volver a Categorías", action: "report_problem" });
        addMessage({ text: "Ok. Ahora, sé más específico:", buttons: subcategories });
    }

    function handleSubcategorySelection(type, params) {
        if (type === 'report_problem') {
            handleMainMenuSelection('report_problem');
            return;
        }
        const subcategoryKey = params[0];
        const categoryKey = state.context.categoryKey;
        state.context.subcategoryKey = subcategoryKey;
        state.current = 'CONFIRMING_ESCALATION';

        const solution = KNOWLEDGE_BASE.casos_soporte[categoryKey].categorias[subcategoryKey];
        const pasos = solution.pasos.join('<br>');
        //  CORREGIDO: Usar <br> en lugar de \n para HTML
        const messageText = `Ok, para <strong>"${solution.titulo}"</strong>, intenta estos pasos:<br><br>${pasos}<br><br>--------------------<br><strong>${solution.titulo_confirmacion}</strong>`;

        addMessage({
            text: messageText,
            buttons: [
                { text: "✅ Sí, se solucionó", action: "solved" },
                { text: "❌ No, necesito ayuda", action: "escalate" }
            ]
        });
    }
    
    async function handleEscalationConfirmation(type) {
        if (type === 'solved') {
            addMessage({ text: "¡Excelente! Me alegra haberte ayudado. 👍 Registrando esto..." });
            try {
                await fetch(`${API_BASE_URL}/tickets/log-solved`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ context: state.context, user: loggedInUser })
                });
            } catch (error) { 
                console.error("Error al registrar ticket resuelto:", error); 
            }
            setTimeout(displayMainMenu, 2000);
            return;
        }
        
        if (type === 'escalate') {
            const solution = KNOWLEDGE_BASE.casos_soporte[state.context.categoryKey].categorias[state.context.subcategoryKey];
            if (solution.opciones_finales && solution.opciones_finales.length > 0) {
                state.current = 'ASKING_FINAL_OPTIONS';
                state.context.finalOptionIndex = 0;
                state.context.finalOptionsTried = [];
                askFinalOption(state.context.finalOptionIndex);
            } else {
                state.current = 'DESCRIBING_ISSUE';
                //  MEJORADO: Mensaje que incluye información sobre archivos
                addMessage({ 
                    text: "📝 <strong>Describe tu problema detalladamente</strong><br><br>Puedes incluir:<br>• Descripción escrita del problema<br>• Capturas de pantalla (usa Ctrl+V para pegarlas)<br>• Documentos relacionados<br>• Cualquier archivo que ayude a entender el problema<br><br>Cuando termines, presiona Enviar." 
                });
                
                //  NUEVO: Mostrar botón de adjuntar archivos
                attachButton.style.display = 'flex';
                attachButton.title = "Adjuntar archivos al ticket";
            }
        }
    }

    function askFinalOption(index) {
        const solution = KNOWLEDGE_BASE.casos_soporte[state.context.categoryKey].categorias[state.context.subcategoryKey];
        const finalOptions = solution.opciones_finales;
        if (index >= finalOptions.length) {
            state.current = 'DESCRIBING_ISSUE';
            addMessage({ text: "Gracias por confirmar. Ahora sí, por favor, describe tu problema." });
            
            //  NUEVO: Mostrar botón de adjuntar archivos
            attachButton.style.display = 'flex';
            attachButton.title = "Adjuntar archivos al ticket";
        } else {
            const option = finalOptions[index];
            const messageText = `Ok, una última cosa:<br><br><strong>${option.titulo}</strong><br>${option.descripcion}`;
            addMessage({
                text: messageText,
                buttons: [
                    { text: "✅ Sí, esto lo solucionó", action: `final_option_solved:${index}` },
                    { text: "❌ No, el problema persiste", action: `final_option_failed:${index}` }
                ]
            });
        }
    }

    // --- LÓGICA MODIFICADA PARA ENTRADA DE TEXTO ---
    async function handleTextInput() {
        const text = userInput.value.trim();
        if (!text) return;
        
        addMessage({ text }, 'user');
        userInput.value = '';
        
        logInteraction({ 
            actionType: 'envio_texto', 
            actionValue: text 
        });
        
        showTypingIndicator();

        setTimeout(async () => {
            if (state.current === 'DESCRIBING_ISSUE') {
                state.context.problemDescription = text;
                
               attachButton.style.display = 'none';
            const previewContainer = document.getElementById('filePreview');
            if (previewContainer) previewContainer.remove();
            
            //  Llamar correctamente a la función de preferencia
            await askAdminPreference();
                
            } else {
                addMessage({ text: "No he entendido. Por favor, usa los botones." });
            }
        }, 1000);
    }
    
    //  NUEVA FUNCIÓN: Crear ticket con archivos adjuntos 
    async function createTicketWithAttachments(preferredAdmin = null) {
        showTypingIndicator();
        
        try {
            // 1. Crear el ticket primero
            const ticketData = { 
                context: state.context, 
                user: loggedInUser 
            };
            
            //  NUEVO: Agregar admin preferido si se especificó
            if (preferredAdmin) {
                ticketData.preferred_admin = preferredAdmin;
            }
            
            const ticketResponse = await fetch(`${API_BASE_URL}/tickets`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ticketData)
            });
            
            const ticketResult = await ticketResponse.json();
            
            if (!ticketResponse.ok) throw new Error(ticketResult.error || 'Error creando ticket');
            
            const ticketId = ticketResult.ticket_id;
            
            // 2. Subir archivos adjuntos si existen
            let uploadResults = [];
            if (state.context.attachedFiles.length > 0) {
                uploadResults = await uploadAllFiles(ticketId);
            }
            
            // 3. Mostrar resultado completo
            showFinalResult(ticketResult, uploadResults, preferredAdmin);
            
        } catch (error) {
            console.error('Error al crear ticket con archivos:', error);
            addMessage({ text: `❌ Error al crear el ticket: ${error.message}` });
        }
    }

    async function uploadAllFiles(ticketId) {
        const results = [];
        
        for (const file of state.context.attachedFiles) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('username', loggedInUser.username);
                
                const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    results.push({ success: true, filename: file.name });
                } else {
                    const errorData = await response.json();
                    results.push({ success: false, filename: file.name, error: errorData.error });
                }
            } catch (error) {
                results.push({ success: false, filename: file.name, error: error.message });
            }
        }
        
        return results;
    }

    function showFinalResult(ticketResult, uploadResults, preferredAdmin = null) {
        let message = `✅ <strong>Ticket ${ticketResult.ticket_id} creado exitosamente!</strong>`;
        
        //  CORREGIDO: Mostrar información del admin asignado
        if (ticketResult.assigned_to) {
            message += `<br>👤 Asignado a: <strong>${ticketResult.assigned_to}</strong>`;
            if (preferredAdmin && ticketResult.assigned_to === preferredAdmin) {
                message += ` (tu preferencia)`;
            }
        }
        
        if (uploadResults.length > 0) {
            const successfulUploads = uploadResults.filter(r => r.success).length;
            const failedUploads = uploadResults.filter(r => !r.success).length;
            
            message += `<br><br>📎 Archivos adjuntos:`;
            message += `<br>✅ ${successfulUploads} subido(s) correctamente`;
            
            if (failedUploads > 0) {
                message += `<br>❌ ${failedUploads} fallaron`;
            }
        }
        
        //  CORREGIDO: Usar <br> para saltos de línea en HTML
        message += `<br><br>📋 <strong>Descripción del problema:</strong><br>${state.context.problemDescription}`;
        
        addMessage({ text: message });
        
        // Limpiar archivos adjuntos y preview
        state.context.attachedFiles = [];
        const previewContainer = document.getElementById('filePreview');
        if (previewContainer) previewContainer.remove();
        attachButton.style.display = 'none';
        
        setTimeout(displayMainMenu, 6000);
    }

    // --- FUNCIÓN CORREGIDA: PREGUNTAR PREFERENCIA DE ADMIN ---
    async function askAdminPreference() {
    state.current = 'SELECTING_PREFERENCE';
    try {
        const response = await fetch(`${API_BASE_URL}/admins`);
        const admins = await response.json();
        
        if (!response.ok || admins.length === 0) {
            // Si no hay admins, crear ticket directamente
            addMessage({ text: "ℹ️ No hay técnicos disponibles en este momento. Creando ticket con asignación automática..." });
            await createTicketWithAttachments();
            return;
        }
        
        const buttons = admins.map(admin => ({ 
            text: `👤 ${admin.username}`, 
            action: `set_preference:${admin.username}` 
        }));
        buttons.push({ text: "🎲 Asignación Automática", action: "set_preference:none" });
        
        addMessage({
            text: "👥 <strong>Selecciona un técnico para tu ticket</strong><br><br>Puedes elegir a quien prefieres que revise tu problema, o seleccionar asignación automática.",
            buttons: buttons
        });
        
    } catch (error) {
        console.error("Error al cargar admins:", error);
        // Si hay error, crear ticket sin preferencia
        addMessage({ text: "⚠️ No se pudieron cargar los técnicos. Creando ticket con asignación automática..." });
        await createTicketWithAttachments();
    }
}

    // --- EVENT LISTENERS ---
    sendButton.addEventListener('click', handleTextInput);
    userInput.addEventListener('keypress', (e) => e.key === 'Enter' && handleTextInput());
    chatMessages.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' && e.target.dataset.action) {
            handleAction(e.target.dataset.action);
        }
    });
});