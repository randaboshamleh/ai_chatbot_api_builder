import api from './api'

export interface ChatMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    sources?: Array<{
        document_id: string
        source: string
        page: number
        score: number
    }>
    created_at: string
}

export interface ChatSession {
    id: string
    created_at: string
    messages: ChatMessage[]
}

export interface QueryResponse {
    session_id: string
    answer: string
    sources: Array<any>
    chunks_used: number
}

export const chatService = {
    query: async (question: string, sessionId?: string): Promise<QueryResponse> => {
        const response = await api.post('/chat/query/', {
            question,
            session_id: sessionId,
        })
        return response.data
    },

    getSessions: async (): Promise<ChatSession[]> => {
        const response = await api.get('/chat/sessions/')
        return response.data
    },

    getSession: async (id: string): Promise<ChatSession> => {
        const response = await api.get(`/chat/sessions/${id}/`)
        return response.data
    },

    // Alias for compatibility
    sendQuery: async (data: { query: string; session_id?: string }): Promise<QueryResponse> => {
        return chatService.query(data.query, data.session_id)
    },
}
