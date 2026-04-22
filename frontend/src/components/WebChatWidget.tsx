import { useState, useEffect, useRef } from 'react';
import { Send, X, MessageCircle, Minimize2 } from 'lucide-react';
import axios from 'axios';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    sources?: any[];
}

interface WebChatWidgetProps {
    tenantSlug: string;
    position?: 'bottom-right' | 'bottom-left';
    primaryColor?: string;
}

export default function WebChatWidget({
    tenantSlug,
    position = 'bottom-right',
    primaryColor = '#3B82F6'
}: WebChatWidgetProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [welcomeMessage, setWelcomeMessage] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // For development: use direct API port, for production: use relative path
    const API_BASE = import.meta.env.DEV
        ? 'http://localhost:8000/api/v1/webchat'
        : '/api/v1/webchat';

    // Initialize chat session
    useEffect(() => {
        if (isOpen && !sessionId) {
            initializeChat();
        }
    }, [isOpen]);

    // Scroll to bottom when messages change
    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const initializeChat = async () => {
        try {
            const response = await axios.post(`${API_BASE}/init/`, {
                tenant_slug: tenantSlug,
            });

            setSessionId(response.data.session_id);
            setWelcomeMessage(response.data.welcome_message);

            // Add welcome message
            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: response.data.welcome_message || 'Hello! How can I help you?',
                timestamp: new Date().toISOString(),
            }]);
        } catch (error) {
            console.error('Failed to initialize chat:', error);
        }
    };

    const sendMessage = async () => {
        if (!inputMessage.trim() || !sessionId || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputMessage,
            timestamp: new Date().toISOString(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInputMessage('');
        setIsLoading(true);

        try {
            const response = await axios.post(`${API_BASE}/message/`, {
                session_id: sessionId,
                message: inputMessage,
            });

            const assistantMessage: Message = {
                id: response.data.message_id,
                role: 'assistant',
                content: response.data.response,
                timestamp: response.data.timestamp,
                sources: response.data.sources,
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Failed to send message:', error);

            const errorMessage: Message = {
                id: Date.now().toString(),
                role: 'assistant',
                content: 'Sorry, an error occurred. Please try again.',
                timestamp: new Date().toISOString(),
            };

            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const positionClasses = position === 'bottom-right'
        ? 'bottom-4 right-4'
        : 'bottom-4 left-4';

    return (
        <div className={`fixed ${positionClasses} z-50`}>
            {/* Chat Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="rounded-full p-4 shadow-lg hover:shadow-xl transition-all"
                    style={{ backgroundColor: primaryColor }}
                >
                    <MessageCircle className="w-6 h-6 text-white" />
                </button>
            )}

            {/* Chat Window */}
            {isOpen && (
                <div
                    className={`bg-white rounded-lg shadow-2xl flex flex-col transition-all ${isExpanded
                        ? 'fixed inset-4 w-auto h-auto'
                        : 'w-96 h-[600px]'
                        }`}
                >
                    {/* Header */}
                    <div
                        className="p-4 rounded-t-lg flex items-center justify-between flex-shrink-0"
                        style={{ backgroundColor: primaryColor }}
                    >
                        <div className="flex items-center gap-2">
                            <MessageCircle className="w-5 h-5 text-white" />
                            <h3 className="text-white font-semibold">Chat Assistant</h3>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setIsExpanded(!isExpanded)}
                                className="text-white hover:bg-white/20 p-1 rounded transition-colors"
                                title={isExpanded ? 'تصغير' : 'تكبير'}
                            >
                                <Minimize2 className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="text-white hover:bg-white/20 p-1 rounded transition-colors"
                                title="إغلاق"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0" dir="ltr">
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`max-w-[80%] rounded-lg p-3 ${message.role === 'user'
                                        ? 'bg-blue-500 text-white text-left'
                                        : 'bg-gray-100 text-gray-800 text-left'
                                        }`}
                                >
                                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                                    {message.sources && message.sources.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-gray-300">
                                            <p className="text-xs font-semibold opacity-75 mb-2 text-left">Sources:</p>
                                            <div className="space-y-1">
                                                {message.sources.map((source, idx) => (
                                                    <div key={idx} className="text-xs opacity-75 bg-white/50 px-2 py-1 rounded text-left">
                                                        📄 {source.source || source.title || source.filename || `Source ${idx + 1}`}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-gray-100 rounded-lg p-3">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="p-4 border-t flex-shrink-0" dir="ltr">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type your message..."
                                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:border-transparent text-left"
                                style={{ '--tw-ring-color': primaryColor } as any}
                                disabled={isLoading}
                                dir="ltr"
                            />
                            <button
                                onClick={sendMessage}
                                disabled={isLoading || !inputMessage.trim()}
                                className="rounded-lg p-2 text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
                                style={{ backgroundColor: primaryColor }}
                            >
                                <Send className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
