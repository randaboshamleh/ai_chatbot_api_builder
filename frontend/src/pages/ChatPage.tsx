import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from 'react-query'
import { Send, Bot, Sparkles, FileText, Upload, User, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import DashboardLayout from '../components/Layout/DashboardLayout'
import { chatService } from '../services/chatService'
import { documentService } from '../services/documentService'
import { splitTextByDirection } from '../utils/textDirection'

export default function ChatPage() {
    const { t } = useTranslation()
    const [messages, setMessages] = useState<any[]>([])
    const [input, setInput] = useState('')
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const { data: documents, isLoading: documentsLoading } = useQuery(
        'documents',
        documentService.list,
        {
            staleTime: 30000, // Cache for 30 seconds
            refetchOnWindowFocus: false,
        }
    )

    const hasIndexedDocuments = documents && Array.isArray(documents) && documents.some((doc: any) => doc.status === 'indexed')
    const hasProcessingDocuments = documents && Array.isArray(documents) && documents.some((doc: any) => doc.status === 'processing')

    const queryMutation = useMutation(chatService.sendQuery, {
        onSuccess: (data) => {
            // Deduplicate sources by filename
            const uniqueSources = data.sources
                ? [...new Map(data.sources.map((s: any) => {
                    const key = typeof s === 'string' ? s : (s.source || s)
                    return [key, s]
                })).values()]
                : []
            setMessages(prev => [...prev, { role: 'assistant', content: data.answer, sources: uniqueSources }])
        },
        onError: (error: any) => {
            console.error('Chat query error:', error)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: t('chat.errorProcessing'),
                error: true
            }])
        },
    })

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || queryMutation.isLoading) return
        const msg = input.trim()
        setInput('')
        setMessages(prev => [...prev, { role: 'user', content: msg }])
        queryMutation.mutate({ query: msg })
    }

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    return (
        <DashboardLayout>
            <div className="h-[calc(100vh-120px)] flex flex-col">
                {documentsLoading ? (
                    <div className="flex-1 flex items-center justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                    </div>
                ) : !hasIndexedDocuments ? (
                    <div className="flex-1 flex items-center justify-center p-8">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="max-w-md text-center"
                        >
                            <div className="relative mb-8">
                                <div className="absolute inset-0 bg-gradient-to-r from-primary-400 to-purple-400 blur-3xl opacity-20"></div>
                                <div className="relative inline-flex p-6 rounded-3xl bg-gradient-to-br from-primary-50 to-purple-50 border border-primary-100">
                                    <FileText className="w-16 h-16 text-primary-600" />
                                </div>
                            </div>
                            <h3 className="text-2xl font-black text-gray-900 mb-3">
                                {t('chat.noDocumentsReady')}
                            </h3>
                            <p className="text-gray-600 mb-6 leading-relaxed">
                                {t('chat.noDocumentsDesc')}
                            </p>
                            {hasProcessingDocuments && (
                                <div className="flex items-center justify-center gap-2 text-amber-600 mb-6 bg-amber-50 py-3 px-4 rounded-xl">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <p className="text-sm font-medium">
                                        {t('chat.documentsProcessing')}
                                    </p>
                                </div>
                            )}
                            <Link
                                to="/documents"
                                data-testid="chat-go-documents-link"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-xl hover:from-primary-700 hover:to-primary-800 transition-all shadow-lg shadow-primary-200 font-semibold"
                            >
                                <Upload className="w-5 h-5" />
                                {t('chat.goToDocuments')}
                            </Link>
                        </motion.div>
                    </div>
                ) : (
                    <>
                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto">
                            <div className="max-w-4xl mx-auto px-4 py-8">
                                <AnimatePresence initial={false}>
                                    {messages.length === 0 && (
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            className="flex items-center justify-center min-h-[50vh] ml-8"
                                        >
                                            <div className="text-center max-w-md">
                                                <div className="inline-flex p-5 rounded-3xl bg-gradient-to-br from-primary-50 to-purple-50 mb-4">
                                                    <Sparkles className="w-10 h-10 text-primary-600" />
                                                </div>
                                                <h3 className="text-xl font-bold text-gray-900 mb-2">
                                                    {t('chat.aiAssistant')}
                                                </h3>
                                                <p className="text-gray-600 text-sm">
                                                    {t('chat.startConversation')}
                                                </p>
                                            </div>
                                        </motion.div>
                                    )}
                                    {messages.map((msg, idx) => (
                                        <motion.div
                                            key={idx}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ duration: 0.3 }}
                                            className={`flex gap-4 mb-8 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                        >
                                            {msg.role === 'assistant' && (
                                                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center shadow-lg">
                                                    <Bot className="w-5 h-5 text-white" />
                                                </div>
                                            )}
                                            <div className={`flex-1 max-w-3xl ${msg.role === 'user' ? 'flex justify-end' : ''}`}>
                                                <div className={`${msg.role === 'user'
                                                    ? 'bg-gradient-to-br from-primary-600 to-primary-700 text-white'
                                                    : 'bg-white border border-gray-200'
                                                    } rounded-2xl px-6 py-4 shadow-sm`}>
                                                    <div className="space-y-1">
                                                        {splitTextByDirection(msg.content).map((segment, segmentIdx) => (
                                                            <p
                                                                key={`${idx}-${segmentIdx}`}
                                                                className={`leading-relaxed whitespace-pre-wrap break-words ${msg.role === 'user' ? 'text-white' : 'text-gray-800'}`}
                                                                dir="auto"
                                                                style={{
                                                                    direction: segment.dir,
                                                                    unicodeBidi: 'plaintext',
                                                                    textAlign: segment.dir === 'rtl' ? 'right' : 'left',
                                                                }}
                                                            >
                                                                {segment.text}
                                                            </p>
                                                        ))}
                                                    </div>
                                                    {msg.sources && msg.sources.length > 0 && (
                                                        <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap gap-2 items-center">
                                                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                                                {t('chat.sources')}:
                                                            </span>
                                                            {msg.sources.map((s: any, i: number) => (
                                                                <span key={i} className="text-xs bg-gray-100 text-gray-700 px-3 py-1 rounded-full font-medium">
                                                                    {typeof s === 'string' ? s : s.source || `Source ${i + 1}`}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                            {msg.role === 'user' && (
                                                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center shadow-lg">
                                                    <User className="w-5 h-5 text-white" />
                                                </div>
                                            )}
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                                {queryMutation.isLoading && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="flex gap-4 mb-8"
                                    >
                                        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center shadow-lg">
                                            <Bot className="w-5 h-5 text-white" />
                                        </div>
                                        <div className="bg-white border border-gray-200 rounded-2xl px-6 py-4 shadow-sm">
                                            <div className="flex gap-1.5">
                                                <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                                <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                                <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" />
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>
                        </div>

                        {/* Input Area */}
                        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-50 ml-20">
                            <form onSubmit={handleSubmit} className="relative">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder={t('chat.askQuestion')}
                                    disabled={!hasIndexedDocuments || queryMutation.isLoading}
                                    data-testid="chat-input"
                                    className="w-full px-5 py-3 pr-12 glass-effect rounded-xl focus:ring-2 focus:ring-primary-400 transition-all outline-none disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 placeholder-gray-500"
                                />
                                <button
                                    type="submit"
                                    disabled={!input.trim() || queryMutation.isLoading || !hasIndexedDocuments}
                                    data-testid="chat-send-button"
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-gradient-to-r from-primary-600 to-cyan-600 text-white rounded-lg hover:from-primary-700 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg disabled:shadow-none"
                                >
                                    <Send className="w-4 h-4" />
                                </button>
                            </form>
                        </div>
                    </>
                )}
            </div>
        </DashboardLayout>
    )
}
