import api from './api'

export interface LoginData {
    username: string
    password: string
}

export interface RegisterData {
    company_name: string
    slug: string
    username: string
    email: string
    password: string
}

export const authService = {
    login: async (data: LoginData) => {
        const response = await api.post('/auth/login/', data)
        return response.data
    },

    register: async (data: RegisterData) => {
        const response = await api.post('/auth/register/', data)
        return response.data
    },

    logout: async (refreshToken: string) => {
        const response = await api.post('/auth/logout/', { refresh: refreshToken })
        return response.data
    },
}
