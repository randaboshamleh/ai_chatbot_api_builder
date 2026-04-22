/**
 * AI Chatbot Web Widget
 * Standalone JavaScript widget for embedding AI chatbot on any website
 */

(function () {
    'use strict';

    // Configuration
    let config = {
        apiBaseUrl: window.location.origin,
        tenantSlug: '',
        position: 'bottom-right',
        primaryColor: '#3B82F6',
        welcomeMessage: 'مرحباً! كيف يمكنني مساعدتك؟'
    };

    let sessionId = null;
    let messages = [];
    let isOpen = false;
    let isExpanded = false;
    let isLoading = false;

    // Create widget HTML
    function createWidget() {
        const widgetContainer = document.createElement('div');
        widgetContainer.id = 'ai-chatbot-widget';
        widgetContainer.style.cssText = `
            position: fixed;
            ${config.position === 'bottom-right' ? 'bottom: 20px; right: 20px;' : 'bottom: 20px; left: 20px;'}
            z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

        // Chat button
        const chatButton = document.createElement('button');
        chatButton.id = 'ai-chatbot-button';
        chatButton.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        `;
        chatButton.style.cssText = `
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: ${config.primaryColor};
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        `;
        chatButton.onmouseover = () => chatButton.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
        chatButton.onmouseout = () => chatButton.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        chatButton.onclick = toggleChat;

        // Chat window
        const chatWindow = document.createElement('div');
        chatWindow.id = 'ai-chatbot-window';
        chatWindow.style.cssText = `
            display: none;
            flex-direction: column;
            width: 380px;
            height: 600px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            overflow: hidden;
        `;

        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            background: ${config.primaryColor};
            color: white;
            padding: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        `;
        header.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span style="font-weight: 600;">Chat Assistant</span>
            </div>
            <button id="ai-chatbot-close" style="background: none; border: none; color: white; cursor: pointer; padding: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;

        // Messages container
        const messagesContainer = document.createElement('div');
        messagesContainer.id = 'ai-chatbot-messages';
        messagesContainer.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            background: #f9fafb;
            direction: ltr;
        `;

        // Input container
        const inputContainer = document.createElement('div');
        inputContainer.style.cssText = `
            padding: 16px;
            border-top: 1px solid #e5e7eb;
            background: white;
            direction: ltr;
        `;
        inputContainer.innerHTML = `
            <div style="display: flex; gap: 8px;">
                <input 
                    type="text" 
                    id="ai-chatbot-input" 
                    placeholder="Type your message..."
                    style="flex: 1; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; outline: none; font-size: 14px; direction: ltr; text-align: left;"
                />
                <button 
                    id="ai-chatbot-send"
                    style="padding: 12px 16px; background: ${config.primaryColor}; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;"
                >
                    Send
                </button>
            </div>
        `;

        chatWindow.appendChild(header);
        chatWindow.appendChild(messagesContainer);
        chatWindow.appendChild(inputContainer);

        widgetContainer.appendChild(chatButton);
        widgetContainer.appendChild(chatWindow);
        document.body.appendChild(widgetContainer);

        // Event listeners
        document.getElementById('ai-chatbot-close').onclick = toggleChat;
        document.getElementById('ai-chatbot-send').onclick = sendMessage;
        document.getElementById('ai-chatbot-input').onkeypress = (e) => {
            if (e.key === 'Enter') sendMessage();
        };
    }

    function toggleChat() {
        isOpen = !isOpen;
        const button = document.getElementById('ai-chatbot-button');
        const window = document.getElementById('ai-chatbot-window');

        if (isOpen) {
            button.style.display = 'none';
            window.style.display = 'flex';
            if (!sessionId) initializeChat();
        } else {
            button.style.display = 'flex';
            window.style.display = 'none';
        }
    }

    async function initializeChat() {
        try {
            const response = await fetch(`${config.apiBaseUrl}/api/v1/webchat/init/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tenant_slug: config.tenantSlug })
            });

            const data = await response.json();
            sessionId = data.session_id;

            addMessage('assistant', data.welcome_message || config.welcomeMessage);
        } catch (error) {
            console.error('Failed to initialize chat:', error);
            addMessage('assistant', 'Sorry, connection error occurred.');
        }
    }

    async function sendMessage() {
        const input = document.getElementById('ai-chatbot-input');
        const message = input.value.trim();

        if (!message || isLoading) return;

        input.value = '';
        addMessage('user', message);
        isLoading = true;

        try {
            const response = await fetch(`${config.apiBaseUrl}/api/v1/webchat/message/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: message
                })
            });

            const data = await response.json();
            addMessage('assistant', data.response, data.sources);
        } catch (error) {
            console.error('Failed to send message:', error);
            addMessage('assistant', 'Sorry, an error occurred. Please try again.');
        } finally {
            isLoading = false;
        }
    }

    function addMessage(role, content, sources = []) {
        const container = document.getElementById('ai-chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            display: flex;
            ${role === 'user' ? 'justify-content: flex-end;' : 'justify-content: flex-start;'}
            margin-bottom: 12px;
        `;

        const bubble = document.createElement('div');
        bubble.style.cssText = `
            max-width: 80%;
            padding: 12px;
            border-radius: 12px;
            ${role === 'user'
                ? 'background: ' + config.primaryColor + '; color: white;'
                : 'background: white; color: #1f2937; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'
            }
            direction: ltr;
            text-align: left;
        `;

        bubble.innerHTML = `<p style="margin: 0; font-size: 14px; line-height: 1.5; white-space: pre-wrap;">${content}</p>`;

        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.style.cssText = 'margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb;';
            sourcesDiv.innerHTML = `
                <p style="font-size: 11px; font-weight: 600; margin: 0 0 4px 0; opacity: 0.7; text-align: left;">Sources:</p>
                ${sources.map(s => `
                    <div style="font-size: 11px; opacity: 0.7; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 4px; margin-bottom: 4px; text-align: left;">
                        📄 ${s.source || s.title || 'Source'}
                    </div>
                `).join('')}
            `;
            bubble.appendChild(sourcesDiv);
        }

        messageDiv.appendChild(bubble);
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
    }

    // Public API
    window.WebChat = {
        init: function (options) {
            config = { ...config, ...options };

            if (!config.tenantSlug) {
                console.error('WebChat: tenantSlug is required');
                return;
            }

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', createWidget);
            } else {
                createWidget();
            }
        }
    };
})();
