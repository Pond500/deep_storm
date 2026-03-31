// Global state
let currentMode = 'storm'; // 'storm' or 'costorm'
let isGenerating = false;
let chatHistory = [];
let ws = null;  // WebSocket connection

// Global reference storage
let currentReferences = {};

// Default settings
let settings = {
    storm: {
        max_conv_turn: 5,
        max_perspective: 4,
        search_top_k: 5,
        max_search_queries_per_turn: 2,
        retrieve_top_k: 5
    },
    costorm: {
        total_conv_turn: 20,
        retrieve_top_k: 5,
        max_search_queries: 3,
        warmstart_max_num_experts: 2,
        warmstart_max_turn_per_experts: 2,
        max_num_round_table_experts: 2
    }
};

// Load settings from localStorage
function loadSettings() {
    const saved = localStorage.getItem('storm_settings');
    if (saved) {
        try {
            settings = JSON.parse(saved);
        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    }
}

// Save settings to localStorage
function saveSettingsToStorage() {
    localStorage.setItem('storm_settings', JSON.stringify(settings));
}

// Initialize settings on page load
loadSettings();

// Progress stages for STORM
const STORM_STAGES = {
    'setup': { icon: '🔧', label: 'เตรียมระบบ' },
    'config': { icon: '⚙️', label: 'ตั้งค่าโมเดล' },
    'retrieval': { icon: '🔍', label: 'เชื่อมต่อฐานข้อมูล' },
    'init': { icon: '✅', label: 'ระบบพร้อม' },
    'research': { icon: '📚', label: 'ค้นคว้าข้อมูล' },
    'outline': { icon: '📝', label: 'สร้างโครงร่าง' },
    'writing': { icon: '✍️', label: 'เขียนบทความ' },
    'polish': { icon: '✨', label: 'ปรับปรุงบทความ' },
    'complete': { icon: '🎉', label: 'เสร็จสมบูรณ์' }
};

// Progress stages for Co-STORM
const COSTORM_STAGES = {
    'setup': { icon: '🔧', label: 'เตรียมระบบ' },
    'config': { icon: '⚙️', label: 'ตั้งค่าโมเดล' },
    'retrieval': { icon: '🔍', label: 'เชื่อมต่อฐานข้อมูล' },
    'init': { icon: '✅', label: 'ระบบพร้อม' },
    'warmstart': { icon: '🌟', label: 'สร้างผู้เชี่ยวชาญ' },
    'conversation': { icon: '💬', label: 'สนทนากับผู้เชี่ยวชาญ' },
    'writing': { icon: '✍️', label: 'เขียนบทความ' },
    'complete': { icon: '🎉', label: 'เสร็จสมบูรณ์' }
};

// Mode Selection
function selectMode(mode) {
    currentMode = mode;

    // Update button states
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

    // Update mode indicator
    const modeIndicator = document.getElementById('modeIndicator');
    const modeText = mode === 'storm' ? 'STORM (อัตโนมัติ)' : 'Co-STORM (โต้ตอบ)';
    modeIndicator.innerHTML = `
        <span class="mode-dot"></span>
        <span>โหมด: ${modeText}</span>
    `;

    // Update placeholder
    const input = document.getElementById('topicInput');
    if (mode === 'storm') {
        input.placeholder = 'พิมพ์หัวข้อที่ต้องการสร้างบทความ...';
    } else {
        input.placeholder = 'พิมพ์หัวข้อเพื่อเริ่มการสนทนาแบบโต้ตอบ...';
    }
}

// New Chat
function newChat() {
    // Hide messages, show welcome screen
    document.getElementById('messages').style.display = 'none';
    document.getElementById('welcomeScreen').style.display = 'block';
    document.getElementById('topicInput').value = '';
    isGenerating = false;
}

// Use suggested prompt
function usePrompt(prompt) {
    document.getElementById('topicInput').value = prompt;
    document.getElementById('topicInput').focus();
}

// Generate Article
async function generateArticle() {
    const input = document.getElementById('topicInput');
    const topic = input.value.trim();

    if (!topic || isGenerating) return;

    isGenerating = true;

    // Hide welcome screen, show messages
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('messages').style.display = 'block';

    // Add user message
    addMessage('user', topic);

    // Clear input
    input.value = '';

    // Add assistant message with loading state
    const messageId = addMessage('assistant', '', true);

    // Create client ID from topic (must match backend's MD5 hash)
    const clientId = await hashString(topic);
    console.log('🔑 Frontend client_id:', clientId);

    // Connect WebSocket FIRST and wait for connection
    const wsConnected = new Promise((resolve) => {
        connectWebSocket(clientId, messageId, resolve);
    });

    // Wait for WebSocket to connect (max 2 seconds)
    await Promise.race([
        wsConnected,
        new Promise(resolve => setTimeout(resolve, 2000))
    ]);

    console.log('📞 Calling API...');

    try {
        // Prepare request body with settings
        const requestBody = {
            topic: topic,
            mode: currentMode,
            settings: currentMode === 'storm' ? settings.storm : settings.costorm
        };

        console.log('📤 Sending settings:', requestBody.settings);

        // Call API
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error('การสร้างบทความล้มเหลว');
        }

        const data = await response.json();

        // Process references if available
        let processedArticle = data.article;
        let references = {};

        // First: render markdown to HTML
        processedArticle = renderMarkdown(processedArticle);

        // Second: add reference tooltips
        if (data.metadata && data.metadata.references) {
            references = data.metadata.references;
            processedArticle = addReferenceTooltips(processedArticle, references);
        }

        // Update message with result
        updateMessage(messageId, processedArticle, false);

        // Add to history (with references for tooltips)
        addToHistory(topic, processedArticle, references);

    } catch (error) {
        console.error('Error:', error);
        updateMessage(messageId, `❌ เกิดข้อผิดพลาด: ${error.message}`, false);
    } finally {
        isGenerating = false;
        if (ws) {
            ws.close();
            ws = null;
        }
    }
}

// Render markdown to HTML
function renderMarkdown(text) {
    if (!text) return '';

    return text
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

// Add clickable reference tooltips to article
function addReferenceTooltips(article, references) {
    // Store references globally
    currentReferences = references;

    // Replace [1], [2], etc. with clickable links
    return article.replace(/\[(\d+)\]/g, (match, num) => {
        const ref = references[num];
        if (!ref) return match;

        const url = escapeHtml(ref.url);

        // Simple link with only data-ref attribute
        return `<a href="${url}" target="_blank" class="reference-link" data-ref="${num}">[${num}]</a>`;
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show reference tooltip
function showRefTooltip(element) {
    const refNum = element.dataset.ref;
    const ref = currentReferences[refNum];
    if (!ref) return;

    const title = ref.title;
    const snippet = ref.snippet.substring(0, 200) + (ref.snippet.length > 200 ? '...' : '');

    // Remove existing tooltip
    hideRefTooltip();

    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.id = 'ref-tooltip';
    tooltip.className = 'reference-tooltip';
    tooltip.innerHTML = `
        <div class="tooltip-title">${escapeHtml(title)}</div>
        <div class="tooltip-snippet">${escapeHtml(snippet)}</div>
        <div class="tooltip-hint">คลิกเพื่อเปิดหน้า Wikipedia</div>
    `;

    document.body.appendChild(tooltip);

    // Position tooltip
    const rect = element.getBoundingClientRect();
    tooltip.style.left = `${rect.left}px`;
    tooltip.style.top = `${rect.bottom + 5}px`;

    // Adjust if tooltip goes off screen
    const tooltipRect = tooltip.getBoundingClientRect();
    if (tooltipRect.right > window.innerWidth) {
        tooltip.style.left = `${window.innerWidth - tooltipRect.width - 10}px`;
    }
    if (tooltipRect.bottom > window.innerHeight) {
        tooltip.style.top = `${rect.top - tooltipRect.height - 5}px`;
    }
}

// Hide reference tooltip
function hideRefTooltip() {
    const tooltip = document.getElementById('ref-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Hash string for client ID (using SHA-256, same as backend should use)
async function hashString(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);

    try {
        // Use SHA-256 (MD5 not available in Web Crypto API)
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        console.log('🔑 Hash created:', hash.substring(0, 16) + '...');
        return hash;
    } catch (error) {
        // Fallback to simple hash
        console.warn('⚠️ Crypto not available, using fallback hash');
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(16).padStart(8, '0');
    }
}

// Connect WebSocket for progress updates
function connectWebSocket(clientId, messageId, onConnected) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;

    console.log('🔌 Connecting WebSocket...');
    console.log('   URL:', wsUrl);
    console.log('   Client ID:', clientId);
    console.log('   Message ID:', messageId);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('✅ WebSocket CONNECTED!');
        if (onConnected) onConnected();
    };

    ws.onmessage = (event) => {
        console.log('📨 Progress Update:', event.data);
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
            console.log('   Step:', data.step);
            console.log('   Progress:', data.progress + '%');
            console.log('   Message:', data.message);
            updateProgress(messageId, data.step, data.progress, data.message);
        } else if (data.type === 'question') {
            console.log('   Question:', data.question);
            console.log('   Context:', data.context);
            showQuestionInput(messageId, data.question, data.context, clientId);
        }
    };

    ws.onerror = (error) => {
        console.error('❌ WebSocket ERROR:', error);
    };

    ws.onclose = () => {
        console.log('🔌 WebSocket CLOSED');
    };
}

// Update progress in message
function updateProgress(messageId, step, progress, message) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;

    const textDiv = messageDiv.querySelector('.message-text');
    const stages = currentMode === 'storm' ? STORM_STAGES : COSTORM_STAGES;
    const stage = stages[step] || { icon: '⏳', label: 'กำลังดำเนินการ' };

    textDiv.innerHTML = `
        <div class="progress-container">
            <div class="progress-header">
                <span class="progress-icon">${stage.icon}</span>
                <span class="progress-label">${stage.label}</span>
                <span class="progress-percent">${progress}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="progress-message">${message}</div>
        </div>
    `;

    // Scroll to bottom
    const container = messageDiv.closest('.chat-container');
    container.scrollTop = container.scrollHeight;
}

// Add message to chat
function addMessage(role, content, isLoading = false) {
    const messagesContainer = document.getElementById('messages');
    const messageId = `msg-${Date.now()}`;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.id = messageId;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const header = document.createElement('div');
    header.className = 'message-header';

    const author = document.createElement('div');
    author.className = 'message-author';
    author.textContent = role === 'user' ? 'คุณ' : 'STORM Assistant';

    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString('th-TH', {
        hour: '2-digit',
        minute: '2-digit'
    });

    header.appendChild(author);
    header.appendChild(time);

    const text = document.createElement('div');
    text.className = 'message-text';

    if (isLoading) {
        const status = document.createElement('div');
        status.className = 'message-status';
        status.innerHTML = `
            <div class="spinner"></div>
            <span>กำลังสร้างบทความ...</span>
        `;
        text.appendChild(status);
    } else {
        // Use innerHTML for article content (to support reference links)
        text.innerHTML = content;
    }

    contentDiv.appendChild(header);
    contentDiv.appendChild(text);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);

    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageId;
}

// Show question input for Co-STORM interactive mode
function showQuestionInput(messageId, question, context, clientId) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;

    const textDiv = messageDiv.querySelector('.message-text');

    textDiv.innerHTML = `
        <div class="costorm-question">
            <div class="question-header">
                <span class="question-icon">💬</span>
                <span class="question-title">คำถามจาก Co-STORM</span>
            </div>
            <div class="question-content">
                <p class="question-text">${question}</p>
                ${context ? `<p class="question-context">${context}</p>` : ''}
            </div>
            <div class="question-input-container">
                <textarea 
                    id="costorm-input-${messageId}" 
                    class="costorm-input" 
                    placeholder="พิมพ์คำตอบของคุณ..."
                    rows="3"
                ></textarea>
                <div class="question-actions">
                    <button onclick="sendResponse('${messageId}', '${clientId}', 'SKIP')" class="btn-secondary">
                        ⏭️ ข้าม (SKIP)
                    </button>
                    <button onclick="sendResponse('${messageId}', '${clientId}', 'DONE')" class="btn-secondary">
                        ✅ เสร็จสิ้น (DONE)
                    </button>
                    <button onclick="sendUserResponse('${messageId}', '${clientId}')" class="btn-primary">
                        ส่งคำตอบ
                    </button>
                </div>
            </div>
        </div>
    `;

    // Auto-focus on textarea
    setTimeout(() => {
        const input = document.getElementById(`costorm-input-${messageId}`);
        if (input) input.focus();
    }, 100);

    // Scroll to bottom
    const container = messageDiv.closest('.chat-container');
    container.scrollTop = container.scrollHeight;
}

// Send user response to Co-STORM
async function sendUserResponse(messageId, clientId) {
    const input = document.getElementById(`costorm-input-${messageId}`);
    if (!input) return;

    const response = input.value.trim();
    if (!response) {
        alert('กรุณาพิมพ์คำตอบก่อนส่ง');
        return;
    }

    await sendResponse(messageId, clientId, response);
}

// Send response (can be user input, SKIP, or DONE)
async function sendResponse(messageId, clientId, response) {
    console.log(`📤 Sending response: ${response.substring(0, 50)}...`);

    try {
        const res = await fetch('/api/respond', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: clientId,
                response: response
            })
        });

        if (!res.ok) {
            throw new Error('Failed to send response');
        }

        console.log('✅ Response sent successfully');

        // Show loading state
        const messageDiv = document.getElementById(messageId);
        if (messageDiv) {
            const textDiv = messageDiv.querySelector('.message-text');
            textDiv.innerHTML = `
                <div class="message-status">
                    <div class="spinner"></div>
                    <span>กำลังประมวลผลคำตอบ...</span>
                </div>
            `;
        }

    } catch (error) {
        console.error('❌ Error sending response:', error);
        alert('เกิดข้อผิดพลาดในการส่งคำตอบ กรุณาลองใหม่อีกครั้ง');
    }
}

// Update message content
function updateMessage(messageId, content, isLoading = false) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;

    const textDiv = messageDiv.querySelector('.message-text');

    if (isLoading) {
        textDiv.innerHTML = `
            <div class="message-status">
                <div class="spinner"></div>
                <span>กำลังสร้างบทความ...</span>
            </div>
        `;
    } else {
        // Display content (already formatted as HTML)
        textDiv.innerHTML = content;
    }

    // Scroll to bottom
    const container = messageDiv.closest('.chat-container');
    container.scrollTop = container.scrollHeight;
}

// Format article for display
function formatArticle(article) {
    if (!article) return '';

    // Simple markdown-like formatting
    let formatted = article
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    return `
        <div class="article-preview">
            <p>${formatted}</p>
            <button class="download-btn" onclick="downloadArticle()">
                📥 ดาวน์โหลดบทความ
            </button>
        </div>
    `;
}

// Add to chat history
function addToHistory(topic, article, references = {}) {
    chatHistory.unshift({
        topic: topic,
        article: article,
        references: references,
        timestamp: new Date()
    });

    updateHistorySidebar();
    updateArticleCount();
}

// Update history sidebar
function updateHistorySidebar() {
    const historyContainer = document.getElementById('chatHistory');
    historyContainer.innerHTML = '';

    chatHistory.slice(0, 10).forEach((item, index) => {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.textContent = item.topic;
        chatItem.onclick = () => loadHistoryItem(index);
        historyContainer.appendChild(chatItem);
    });
}

// Update article count
function updateArticleCount() {
    document.getElementById('articleCount').textContent = chatHistory.length;
}

// Load history item
function loadHistoryItem(index) {
    const item = chatHistory[index];

    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('messages').style.display = 'block';

    const messagesContainer = document.getElementById('messages');
    messagesContainer.innerHTML = '';

    // Restore references for tooltips
    if (item.references) {
        currentReferences = item.references;
    }

    addMessage('user', item.topic);
    addMessage('assistant', item.article);
}

// Download article
function downloadArticle() {
    if (chatHistory.length === 0) return;

    const latestArticle = chatHistory[0];
    const blob = new Blob([latestArticle.article], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${latestArticle.topic}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Event delegation for reference links (hover and click)
document.addEventListener('DOMContentLoaded', () => {
    const messagesContainer = document.getElementById('messages');

    // Hover events using event delegation
    messagesContainer.addEventListener('mouseover', (e) => {
        if (e.target.classList.contains('reference-link')) {
            showRefTooltip(e.target);
        }
    });

    messagesContainer.addEventListener('mouseout', (e) => {
        if (e.target.classList.contains('reference-link')) {
            hideRefTooltip();
        }
    });

    console.log('SansarnWiki Web UI initialized');
    selectMode('storm');
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Cmd/Ctrl + K for new chat
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        newChat();
    }

    // Cmd/Ctrl + / to focus input
    if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        document.getElementById('topicInput').focus();
    }
});

// ============================================================================
// Settings Modal Functions
// ============================================================================

// Open settings modal
function openSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.add('active');

    // Load current settings into UI
    updateSettingsUI();
}

// Close settings modal
function closeSettings(event) {
    // Close if clicking overlay or explicit close
    if (!event || event.target.id === 'settingsModal') {
        const modal = document.getElementById('settingsModal');
        modal.classList.remove('active');
    }
}

// Switch settings tab
function switchSettingsTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.settings-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

    // Update panels
    document.querySelectorAll('.settings-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`${tab}Settings`).classList.add('active');
}

// Update setting value display
function updateSettingValue(settingId) {
    const input = document.getElementById(settingId);
    const valueSpan = document.getElementById(`${settingId}_value`);
    valueSpan.textContent = input.value;
}

// Update settings UI with current values
function updateSettingsUI() {
    // STORM settings
    document.getElementById('storm_max_conv_turn').value = settings.storm.max_conv_turn;
    document.getElementById('storm_max_conv_turn_value').textContent = settings.storm.max_conv_turn;

    document.getElementById('storm_max_perspective').value = settings.storm.max_perspective;
    document.getElementById('storm_max_perspective_value').textContent = settings.storm.max_perspective;

    document.getElementById('storm_search_top_k').value = settings.storm.search_top_k;
    document.getElementById('storm_search_top_k_value').textContent = settings.storm.search_top_k;

    document.getElementById('storm_max_search_queries').value = settings.storm.max_search_queries_per_turn;
    document.getElementById('storm_max_search_queries_value').textContent = settings.storm.max_search_queries_per_turn;

    document.getElementById('storm_retrieve_top_k').value = settings.storm.retrieve_top_k;
    document.getElementById('storm_retrieve_top_k_value').textContent = settings.storm.retrieve_top_k;

    // Co-STORM settings
    document.getElementById('costorm_total_conv_turn').value = settings.costorm.total_conv_turn;
    document.getElementById('costorm_total_conv_turn_value').textContent = settings.costorm.total_conv_turn;

    document.getElementById('costorm_retrieve_top_k').value = settings.costorm.retrieve_top_k;
    document.getElementById('costorm_retrieve_top_k_value').textContent = settings.costorm.retrieve_top_k;

    document.getElementById('costorm_max_search_queries').value = settings.costorm.max_search_queries;
    document.getElementById('costorm_max_search_queries_value').textContent = settings.costorm.max_search_queries;

    document.getElementById('costorm_warmstart_max_experts').value = settings.costorm.warmstart_max_num_experts;
    document.getElementById('costorm_warmstart_max_experts_value').textContent = settings.costorm.warmstart_max_num_experts;

    document.getElementById('costorm_warmstart_max_turn').value = settings.costorm.warmstart_max_turn_per_experts;
    document.getElementById('costorm_warmstart_max_turn_value').textContent = settings.costorm.warmstart_max_turn_per_experts;

    document.getElementById('costorm_max_round_table_experts').value = settings.costorm.max_num_round_table_experts;
    document.getElementById('costorm_max_round_table_experts_value').textContent = settings.costorm.max_num_round_table_experts;
}

// Save settings
function saveSettings() {
    // Read values from UI
    settings.storm.max_conv_turn = parseInt(document.getElementById('storm_max_conv_turn').value);
    settings.storm.max_perspective = parseInt(document.getElementById('storm_max_perspective').value);
    settings.storm.search_top_k = parseInt(document.getElementById('storm_search_top_k').value);
    settings.storm.max_search_queries_per_turn = parseInt(document.getElementById('storm_max_search_queries').value);
    settings.storm.retrieve_top_k = parseInt(document.getElementById('storm_retrieve_top_k').value);

    settings.costorm.total_conv_turn = parseInt(document.getElementById('costorm_total_conv_turn').value);
    settings.costorm.retrieve_top_k = parseInt(document.getElementById('costorm_retrieve_top_k').value);
    settings.costorm.max_search_queries = parseInt(document.getElementById('costorm_max_search_queries').value);
    settings.costorm.warmstart_max_num_experts = parseInt(document.getElementById('costorm_warmstart_max_experts').value);
    settings.costorm.warmstart_max_turn_per_experts = parseInt(document.getElementById('costorm_warmstart_max_turn').value);
    settings.costorm.max_num_round_table_experts = parseInt(document.getElementById('costorm_max_round_table_experts').value);

    // Save to localStorage
    saveSettingsToStorage();

    // Close modal
    closeSettings();

    console.log('✅ Settings saved:', settings);
}

// Reset settings to default
function resetSettings() {
    if (confirm('รีเซ็ตการตั้งค่าทั้งหมดเป็นค่าเริ่มต้น?')) {
        settings = {
            storm: {
                max_conv_turn: 5,
                max_perspective: 4,
                search_top_k: 5,
                max_search_queries_per_turn: 2,
                retrieve_top_k: 5
            },
            costorm: {
                total_conv_turn: 20,
                retrieve_top_k: 5,
                max_search_queries: 3,
                warmstart_max_num_experts: 2,
                warmstart_max_turn_per_experts: 2,
                max_num_round_table_experts: 2
            }
        };

        saveSettingsToStorage();
        updateSettingsUI();

        console.log('✅ Settings reset to default');
    }
}
