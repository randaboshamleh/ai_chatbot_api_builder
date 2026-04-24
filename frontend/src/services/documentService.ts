import api from './api'

export interface Document {
    id: string
    title: string
    original_filename: string
    file_type: string
    file_size: number
    status: 'pending' | 'processing' | 'indexed' | 'failed'
    chunk_count: number
    created_at: string
    updated_at?: string
    processing_time?: number
    status_message?: string
    estimated_wait_seconds?: number
    poll_interval_seconds?: number
    error_message?: string
}

export const documentService = {
    upload: async (file: File, title?: string) => {
        const formData = new FormData()
        formData.append('file', file)
        if (title) formData.append('title', title)

        const response = await api.post('/documents/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
        return response.data
    },

    list: async (): Promise<Document[]> => {
        const response = await api.get('/documents/')
        // API returns paginated response with results array
        return response.data.results || response.data
    },

    delete: async (id: string) => {
        const response = await api.delete(`/documents/${id}/`)
        return response.data
    },

    getStatus: async (id: string) => {
        const response = await api.get(`/documents/${id}/status/`)
        return response.data
    },

    // Aliases for compatibility
    uploadDocument: async (file: File, title?: string) => {
        return documentService.upload(file, title)
    },

    getDocuments: async (): Promise<Document[]> => {
        return documentService.list()
    },

    deleteDocument: async (id: string) => {
        return documentService.delete(id)
    },

    estimateWaitSeconds: (fileSize: number) => {
        const sizeMb = fileSize / (1024 * 1024)
        if (sizeMb <= 2) return 60
        if (sizeMb <= 10) return 3 * 60
        if (sizeMb <= 25) return 6 * 60
        return 10 * 60
    },
}
