(function () {
    'use strict';

    // Configuration
    const CONFIG = {
        CHAT_ENDPOINT: 'http://localhost:8501', // Your Streamlit app endpoint
        SESSION_TIMEOUT: 30 * 60 * 1000, // 30 minutes in milliseconds
        STORAGE_KEYS: {
            SESSION: 'bytespark_session',
            LEADS: 'bytespark_leads',
            CHAT_STATE: 'chat_state'
        },
        // Professional blue theme colors matching website
        COLORS: {
            PRIMARY: '#2563eb',
            PRIMARY_HOVER: '#1e40af',
            SECONDARY: '#3b82f6',
            BACKGROUND: '#0a0d14',
            SURFACE: 'rgba(255, 255, 255, 0.08)',
            TEXT_PRIMARY: '#ffffff',
            TEXT_SECONDARY: '#f1f5f9',
            BORDER: 'rgba(37, 99, 235, 0.3)',
            ACCENT: 'rgba(37, 99, 235, 0.15)'
        }
    };

    // Session Manager
    class SessionManager {
        constructor() {
            this.currentSession = null;
            this.inactivityTimer = null;
            this.init();
        }

        init() {
            // Load existing session or create new one
            const savedSession = localStorage.getItem(CONFIG.STORAGE_KEYS.SESSION);
            if (savedSession && this.isSessionValid(JSON.parse(savedSession))) {
                this.currentSession = JSON.parse(savedSession);
                this.resetInactivityTimer();
            } else {
                this.createNewSession();
            }

            // Setup visibility change handlers
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    this.pauseInactivityTimer();
                } else {
                    this.resetInactivityTimer();
                }
            });

            // Setup activity listeners
            this.setupActivityListeners();
        }

        createNewSession() {
            this.currentSession = {
                id: this.generateSessionId(),
                startTime: new Date().toISOString(),
                lastActivity: new Date().toISOString(),
                leads: [],
                messages: [],
                isActive: true
            };
            this.saveSession();
        }

        generateSessionId() {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }

        isSessionValid(session) {
            if (!session) return false;
            const sessionAge = new Date() - new Date(session.startTime);
            return sessionAge < 24 * 60 * 60 * 1000; // 24 hours
        }

        resetInactivityTimer() {
            if (this.inactivityTimer) {
                clearTimeout(this.inactivityTimer);
            }
            this.inactivityTimer = setTimeout(() => {
                this.endSession();
            }, CONFIG.SESSION_TIMEOUT);
        }

        pauseInactivityTimer() {
            if (this.inactivityTimer) {
                clearTimeout(this.inactivityTimer);
            }
        }

        setupActivityListeners() {
            const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
            events.forEach(event => {
                document.addEventListener(event, () => this.updateLastActivity());
            });
        }

        updateLastActivity() {
            if (this.currentSession) {
                this.currentSession.lastActivity = new Date().toISOString();
                this.resetInactivityTimer();
            }
        }

        addLead(leadData) {
            if (this.currentSession && !this.currentSession.leads.find(l => l.email === leadData.email)) {
                this.currentSession.leads.push(leadData);
                this.saveSession();
                this.syncWithBackend(leadData);
            }
        }

        addMessage(message) {
            if (this.currentSession) {
                this.currentSession.messages.push({
                    timestamp: new Date().toISOString(),
                    type: 'user',
                    content: message
                });
                this.saveSession();
            }
        }

        saveSession() {
            localStorage.setItem(CONFIG.STORAGE_KEYS.SESSION, JSON.stringify(this.currentSession));
        }

        endSession() {
            if (this.currentSession) {
                this.currentSession.isActive = false;
                this.currentSession.endTime = new Date().toISOString();
                this.saveSession();
                this.syncWithBackend({ type: 'session_end' });

                // Create new session after a short delay
                setTimeout(() => this.createNewSession(), 1000);
            }
        }

        syncWithBackend(data) {
            // Sync with your backend - implement as needed
            console.log('Syncing with backend:', data);
            // You can send this to your Streamlit app via fetch
        }
    }

    // Lead Capture System
    class LeadCapture {
        constructor() {
            this.patterns = {
                name: [
                    /name is\s+([a-zA-Z]+\s+[a-zA-Z]+)/i,
                    /my name is\s+([a-zA-Z]+\s+[a-zA-Z]+)/i,
                    /i'm\s+([a-zA-Z]+\s+[a-zA-Z]+)/i,
                    /i am\s+([a-zA-Z]+\s+[a-zA-Z]+)/i,
                    /this is\s+([a-zA-Z]+\s+[a-zA-Z]+)/i,
                    /([a-zA-Z]+\s+[a-zA-Z]+)\s+here/i,
                    /name\s+([a-zA-Z]+)/i,
                    /call me\s+([a-zA-Z]+\s+[a-zA-Z]+)/i
                ],
                email: [
                    /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/i
                ],
                serviceIntent: {
                    cloud: ['cloud', 'backup', 'hosting', 'server', 'aws', 'azure', 'scalable'],
                    ai_ml: ['dashboard', 'prediction', 'predict', 'analytics', 'data analysis', 'race prediction', 'ai', 'ml', 'machine learning'],
                    website: ['website', 'web', 'site', 'online', 'domain'],
                    app: ['app', 'application', 'mobile', 'ios', 'android'],
                    digital_marketing: ['marketing', 'digital', 'social media', 'ads', 'campaign']
                }
            };
        }

        extractFromText(text) {
            const result = {
                name: null,
                email: null,
                serviceIntent: 'general inquiry'
            };

            // Extract name
            for (const pattern of this.patterns.name) {
                const match = text.match(pattern);
                if (match) {
                    result.name = match[1].trim().replace(/\s+/g, ' ').split(' ').map(word =>
                        word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
                    ).join(' ');
                    break;
                }
            }

            // Extract email
            const emailMatch = text.match(this.patterns.email[0]);
            if (emailMatch) {
                result.email = emailMatch[0].trim();
            }

            // Extract service intent
            const textLower = text.toLowerCase();
            for (const [service, keywords] of Object.entries(this.patterns.serviceIntent)) {
                if (keywords.some(keyword => textLower.includes(keyword))) {
                    result.serviceIntent = service.replace('_', ' ');
                    break;
                }
            }

            return result;
        }
    }

    // Widget UI Manager
    class WidgetManager {
        constructor() {
            this.sessionManager = new SessionManager();
            this.leadCapture = new LeadCapture();
            this.isOpen = false;
            this.init();
        }

        init() {
            this.createWidget();
            this.setupEventListeners();
        }

        createWidget() {
            // Create widget container
            const widget = document.createElement('div');
            widget.id = 'bytespark-widget';
            widget.innerHTML = `
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');
                    
                    #bytespark-widget {
                        position: fixed;
                        bottom: 20px;
                        right: 20px;
                        width: 60px;
                        height: 60px;
                        background: linear-gradient(135deg, ${CONFIG.COLORS.PRIMARY}, ${CONFIG.COLORS.SECONDARY});
                        border-radius: 18px;
                        box-shadow: 
                            0 0 0 1px ${CONFIG.COLORS.BORDER},
                            0 0 30px ${CONFIG.COLORS.ACCENT},
                            0 8px 32px rgba(0, 0, 0, 0.4);
                        cursor: pointer;
                        z-index: 99999;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-family: 'Syne', sans-serif;
                        transition: all 0.3s ease;
                        animation: pulse-glow 3s ease-in-out infinite;
                    }
                    
                    @keyframes pulse-glow {
                        0%, 100% { 
                            box-shadow: 0 0 0 1px rgba(99, 88, 255, 0.4), 0 0 30px rgba(99, 88, 255, 0.25), 0 8px 32px rgba(0,0,0,0.4); 
                        }
                        50% { 
                            box-shadow: 0 0 0 1px rgba(99, 88, 255, 0.6), 0 0 50px rgba(99, 88, 255, 0.4), 0 8px 32px rgba(0,0,0,0.4); 
                        }
                    }
                    
                    #bytespark-widget:hover {
                        transform: scale(1.05);
                        box-shadow: 
                            0 0 0 1px rgba(99, 88, 255, 0.6),
                            0 0 40px rgba(99, 88, 255, 0.35),
                            0 12px 40px rgba(0, 0, 0, 0.5);
                    }
                    
                    #bytespark-chat {
                        position: fixed;
                        bottom: 90px;
                        right: 20px;
                        width: 420px;
                        height: min(650px, 85vh);
                        max-height: 85vh;
                        background: ${CONFIG.COLORS.BACKGROUND};
                        background-image:
                            radial-gradient(ellipse 80% 50% at 20% -10%, ${CONFIG.COLORS.ACCENT} 0%, transparent 60%),
                            radial-gradient(ellipse 60% 40% at 80% 110%, ${CONFIG.COLORS.ACCENT.replace('0.15', '0.10')} 0%, transparent 55%);
                        border-radius: 20px;
                        box-shadow: 
                            0 20px 60px rgba(0, 0, 0, 0.6),
                            0 0 0 1px ${CONFIG.COLORS.BORDER};
                        z-index: 99998;
                        display: none;
                        flex-direction: column;
                        font-family: 'DM Sans', sans-serif;
                        backdrop-filter: blur(20px);
                        border: 1px solid ${CONFIG.COLORS.BORDER.replace('0.3', '0.12')};
                    }
                    
                    #bytespark-chat.open {
                        display: flex;
                        opacity: 1;
                        transform: translateY(0);
                        animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
                    }
                    
                    @keyframes slide-up {
                        from { opacity: 0; transform: translateY(20px); }
                        to   { opacity: 1; transform: translateY(0); }
                    }
                    
                    #chat-header {
                        background: rgba(255, 255, 255, 0.04);
                        backdrop-filter: blur(12px);
                        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                        padding: 20px;
                        border-radius: 20px 20px 0 0;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        position: relative;
                    }
                    
                    .spark-logo-ring {
                        width: 48px;
                        height: 48px;
                        border-radius: 12px;
                        background: linear-gradient(135deg, ${CONFIG.COLORS.PRIMARY}, ${CONFIG.COLORS.SECONDARY});
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 20px;
                        margin-bottom: 12px;
                        box-shadow:
                            0 0 0 1px ${CONFIG.COLORS.BORDER},
                            0 0 20px ${CONFIG.COLORS.ACCENT},
                            0 4px 16px rgba(0, 0, 0, 0.3);
                    }
                    
                    .spark-title {
                        font-family: 'Syne', sans-serif;
                        font-weight: 800;
                        font-size: 1.4rem;
                        letter-spacing: -0.02em;
                        background: linear-gradient(135deg, ${CONFIG.COLORS.TEXT_PRIMARY} 0%, #e2e8f0 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                        margin: 0 0 4px;
                        line-height: 1.1;
                    }
                    
                    .spark-sub {
                        font-family: 'DM Sans', sans-serif;
                        font-weight: 300;
                        font-size: 0.8rem;
                        color: ${CONFIG.COLORS.TEXT_PRIMARY};
                        letter-spacing: 0.04em;
                        margin: 0;
                    }
                    
                    #chat-messages {
                        flex: 1;
                        padding: 20px;
                        overflow-y: auto;
                        display: flex;
                        flex-direction: column;
                        gap: 8px;
                    }
                    
                    .message {
                        animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
                        max-width: 85%;
                        word-wrap: break-word;
                    }
                    
                    .user-message {
                        margin-left: auto;
                        text-align: right;
                    }
                    
                    .user-message .message-content {
                        background: linear-gradient(135deg, ${CONFIG.COLORS.PRIMARY} 0%, ${CONFIG.COLORS.PRIMARY_HOVER} 100%);
                        color: ${CONFIG.COLORS.TEXT_PRIMARY};
                        border-radius: 18px 18px 4px 18px;
                        padding: 12px 18px;
                        font-size: 0.95rem;
                        line-height: 1.6;
                        box-shadow: 0 4px 20px ${CONFIG.COLORS.ACCENT};
                        display: inline-block;
                    }
                    
                    .bot-message {
                        margin-right: auto;
                    }
                    
                    .bot-message .message-content {
                        background: ${CONFIG.COLORS.SURFACE};
                        color: ${CONFIG.COLORS.TEXT_SECONDARY};
                        border: 1px solid ${CONFIG.COLORS.BORDER.replace('0.3', '0.12')};
                        border-radius: 18px 18px 18px 4px;
                        padding: 12px 18px;
                        font-size: 0.95rem;
                        line-height: 1.6;
                        backdrop-filter: blur(12px);
                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 ${CONFIG.COLORS.BORDER.replace('0.3', '0.12')};
                        display: inline-block;
                    }
                    
                    #chat-input {
                        padding: 20px;
                        border-top: 1px solid ${CONFIG.COLORS.BORDER};
                        background: linear-gradient(0deg, rgba(10, 13, 20, 0.98) 70%, transparent);
                        display: flex;
                        gap: 12px;
                        align-items: center;
                    }
                    
                    #chat-input input {
                        flex: 1;
                        padding: 14px 18px;
                        background: ${CONFIG.COLORS.SURFACE};
                        border: 1px solid ${CONFIG.COLORS.BORDER};
                        border-radius: 16px;
                        outline: none;
                        font-size: 0.95rem;
                        font-family: 'DM Sans', sans-serif;
                        color: ${CONFIG.COLORS.TEXT_SECONDARY};
                        backdrop-filter: blur(20px);
                        transition: all 0.2s ease;
                        box-shadow: inset 0 1px 0 ${CONFIG.COLORS.BORDER.replace('0.3', '0.12')};
                    }
                    
                    #chat-input input::placeholder {
                        color: rgba(148, 163, 184, 0.6);
                    }
                    
                    #chat-input input:focus {
                        border-color: ${CONFIG.COLORS.PRIMARY};
                        box-shadow: 
                            0 0 0 3px ${CONFIG.COLORS.BORDER.replace('0.3', '0.12')},
                            inset 0 1px 0 ${CONFIG.COLORS.BORDER.replace('0.3', '0.12')};
                    }
                    
                    #chat-input button {
                        background: linear-gradient(135deg, ${CONFIG.COLORS.PRIMARY}, ${CONFIG.COLORS.PRIMARY_HOVER});
                        color: ${CONFIG.COLORS.TEXT_PRIMARY};
                        border: none;
                        padding: 14px 20px;
                        border-radius: 12px;
                        cursor: pointer;
                        font-weight: 600;
                        font-family: 'DM Sans', sans-serif;
                        box-shadow: 0 4px 12px ${CONFIG.COLORS.ACCENT};
                        transition: all 0.2s ease;
                    }
                    
                    #chat-input button:hover {
                        background: linear-gradient(135deg, ${CONFIG.COLORS.SECONDARY}, ${CONFIG.COLORS.PRIMARY});
                        box-shadow: 0 6px 18px ${CONFIG.COLORS.ACCENT.replace('0.4', '0.55')};
                        transform: scale(1.05);
                    }
                    
                    #minimize-btn {
                        position: absolute;
                        top: 15px;
                        right: 15px;
                        background: rgba(255, 255, 255, 0.1);
                        color: rgba(255, 255, 255, 0.7);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 50%;
                        width: 28px;
                        height: 28px;
                        cursor: pointer;
                        font-size: 14px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        transition: all 0.2s ease;
                    }
                    
                    #minimize-btn:hover {
                        background: rgba(255, 255, 255, 0.2);
                        color: white;
                    }
                    
                    /* Scrollbar styling */
                    #chat-messages::-webkit-scrollbar {
                        width: 6px;
                    }
                    
                    #chat-messages::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    
                    #chat-messages::-webkit-scrollbar-thumb {
                        background: ${CONFIG.COLORS.BORDER};
                        border-radius: 99px;
                    }
                    
                    #chat-messages::-webkit-scrollbar-thumb:hover {
                        background: ${CONFIG.COLORS.PRIMARY};
                    }
                    
                    /* Empty state suggestions */
                    .suggestion-chips {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 8px;
                        margin-top: 20px;
                        justify-content: center;
                    }
                    
                    .suggestion-chip {
                        display: inline-block;
                        background: ${CONFIG.COLORS.SURFACE};
                        border: 1px solid ${CONFIG.COLORS.BORDER};
                        border-radius: 100px;
                        padding: 8px 16px;
                        font-size: 0.85rem;
                        color: ${CONFIG.COLORS.TEXT_PRIMARY};
                        font-family: 'DM Sans', sans-serif;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        white-space: nowrap;
                    }
                    
                    .suggestion-chip:hover {
                        background: ${CONFIG.COLORS.ACCENT};
                        border-color: ${CONFIG.COLORS.PRIMARY};
                        color: ${CONFIG.COLORS.TEXT_PRIMARY};
                    }
                </style>
                
                <div id="bytespark-bubble" title="Spark - ByteSpark AI Assistant">
                    <span style="color: white; font-size: 24px;">✦</span>
                </div>
                
                <div id="bytespark-chat">
                    <div id="chat-header">
                        <div class="spark-logo-ring">✦</div>
                        <div class="spark-title">Spark</div>
                        <div class="spark-sub">AI assistant for ByteSpark · always on</div>
                        <button id="minimize-btn" title="Minimize">−</button>
                    </div>
                    
                    <div id="chat-messages">
                        <div class="suggestion-chips" id="suggestion-chips">
                            <span class="suggestion-chip" data-question="What does Bytespark do?">What does Bytespark do?</span>
                            <span class="suggestion-chip" data-question="What are the services provided by bytespark?">What are the services provided by bytespark?</span>
                        </div>
                    </div>
                    
                    <div id="chat-input">
                        <input type="text" placeholder="Ask Spark anything…" id="message-input">
                        <button id="send-btn">Send</button>
                    </div>
                </div>
            `;

            document.body.appendChild(widget);

            // Get elements
            this.elements = {
                bubble: document.getElementById('bytespark-bubble'),
                chat: document.getElementById('bytespark-chat'),
                messages: document.getElementById('chat-messages'),
                input: document.getElementById('message-input'),
                sendBtn: document.getElementById('send-btn'),
                minimizeBtn: document.getElementById('minimize-btn')
            };

            // Setup event listeners
            this.setupEventListeners();
        }

        setupEventListeners() {
            // Toggle chat
            this.elements.bubble.addEventListener('click', () => this.toggleChat());

            // Minimize
            this.elements.minimizeBtn.addEventListener('click', () => this.minimizeChat());

            // Send message
            this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
            this.elements.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });

            // Suggestion chips click handler
            const chipsContainer = this.elements.messages.querySelector('#suggestion-chips');
            if (chipsContainer) {
                chipsContainer.addEventListener('click', (e) => {
                    if (e.target.classList.contains('suggestion-chip')) {
                        const question = e.target.getAttribute('data-question');
                        if (question) {
                            // Auto-fill and send the question
                            this.elements.input.value = question;
                            this.sendMessage();
                        }
                    }
                });
            }
        }

        toggleChat() {
            this.isOpen = !this.isOpen;
            if (this.isOpen) {
                this.elements.chat.style.display = 'flex';
                this.elements.bubble.style.display = 'none';
                this.elements.input.focus();
            } else {
                this.elements.chat.style.display = 'none';
                this.elements.bubble.style.display = 'flex';
            }
        }

        minimizeChat() {
            this.elements.chat.style.display = 'none';
            this.elements.bubble.style.display = 'flex';
            this.isOpen = false;
        }

        sendMessage() {
            const message = this.elements.input.value.trim();
            if (!message) return;

            // Add user message to chat
            this.addMessage(message, 'user');

            // Extract and save lead information
            const leadData = this.leadCapture.extractFromText(message);
            if (leadData.name && leadData.email) {
                this.sessionManager.addLead(leadData);
                console.log('Lead captured:', leadData);
            }

            // Add to session messages
            this.sessionManager.addMessage(message);

            // Simulate bot response
            this.simulateBotResponse(message);

            // Clear input
            this.elements.input.value = '';

            // Update activity
            this.sessionManager.updateLastActivity();
        }

        addMessage(content, type) {
            // Remove suggestion chips on first message
            const suggestionChips = this.elements.messages.querySelector('.suggestion-chips');
            if (suggestionChips) {
                suggestionChips.remove();
            }

            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;

            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            messageContent.textContent = content;

            messageDiv.appendChild(messageContent);

            this.elements.messages.appendChild(messageDiv);
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        }

        simulateBotResponse(userMessage) {
            // Extract service intent
            const leadData = this.leadCapture.extractFromText(userMessage);

            // Send to actual backend for processing
            this.sendToBackend(userMessage);

            // Show typing indicator while waiting for response
            this.showTypingIndicator();
        }

        sendToBackend(message) {
            // Send message to Streamlit backend
            fetch(CONFIG.CHAT_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionManager.currentSession?.id || 'new_session'
                })
            })
                .then(response => response.json())
                .then(data => {
                    // Hide typing indicator
                    this.hideTypingIndicator();

                    // Extract and save lead information
                    const leadData = this.leadCapture.extractFromText(message);
                    if (leadData.name && leadData.email) {
                        this.sessionManager.addLead(leadData);
                        console.log('Lead captured:', leadData);
                    }

                })
                .catch(error => {
                    console.error('Error sending message:', error);
                    this.hideTypingIndicator();
                    this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
                });
        }

        showTypingIndicator() {
            // Show typing indicator in chat
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot-message';
            typingDiv.innerHTML = `
                <div class="message-content">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 8px; height: 8px; border-radius: 50%; background: ${CONFIG.COLORS.PRIMARY}; animation: pulse 1.5s ease-in-out infinite;"></div>
                        <span style="color: ${CONFIG.COLORS.TEXT_SECONDARY}; font-family: 'DM Sans', sans-serif; font-size: 0.95rem;">Spark is typing...</span>
                    </div>
                </div>
            `;

            const messagesContainer = this.elements.messages;
            if (messagesContainer.lastChild) {
                messagesContainer.appendChild(typingDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        hideTypingIndicator() {
            // Remove typing indicator
            const typingIndicator = this.elements.messages.querySelector('.message.bot-message:last-child');
            if (typingIndicator && typingIndicator.textContent.includes('Spark is typing')) {
                typingIndicator.remove();
            }
        }
    }

    // Initialize widget when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        new WidgetManager();
    });

})();
