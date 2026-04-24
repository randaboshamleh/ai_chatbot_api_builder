import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const BASE_URL =
    (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
    (import.meta.env.VITE_API_URL as string | undefined)?.trim() ||
    '/api/v1'

const api = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Separate instance for retries to avoid interceptor loops
const retryApi = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

retryApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

let isRefreshing = false
let failedQueue: Array<{ resolve: (value: string | null) => void; reject: (reason?: any) => void }> = []

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error)
        } else {
            prom.resolve(token)
        }
    })
    failedQueue = []
}

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config
        const requestUrl = originalRequest?.url || ''
        const isAuthEntryRequest = requestUrl.includes('/auth/login/') || requestUrl.includes('/auth/register/')

        const status = error.response?.status
        if (status === 502) {
            error.response.data = {
                error: 'الخادم غير متاح حالياً (502). تأكد أن خدمة API شغالة على المنفذ 8000 أو عبر Nginx.',
            }
        }

        if (!status) {
            error.response = {
                status: 0,
                data: {
                    error: 'تعذر الاتصال بالخادم. تأكد أن الـ API شغالة.',
                },
            }
        }

        if (status === 401 && !originalRequest._retry && !isAuthEntryRequest) {
            if (isRefreshing) {
                return new Promise<string | null>((resolve, reject) => {
                    failedQueue.push({ resolve, reject })
                })
                    .then((token) => {
                        originalRequest.headers.Authorization = `Bearer ${token}`
                        return retryApi(originalRequest)
                    })
                    .catch((err) => Promise.reject(err))
            }

            originalRequest._retry = true
            isRefreshing = true

            const refreshToken = localStorage.getItem('refresh_token')
            if (!refreshToken) {
                isRefreshing = false
                useAuthStore.getState().logout()
                window.location.href = '/login'
                return Promise.reject(error)
            }

            try {
                const response = await retryApi.post('/auth/token/refresh/', {
                    refresh: refreshToken,
                })
                const newToken = response.data.access

                useAuthStore.getState().setToken(newToken)
                localStorage.setItem('access_token', newToken)

                originalRequest.headers.Authorization = `Bearer ${newToken}`
                processQueue(null, newToken)

                isRefreshing = false
                return retryApi(originalRequest)
            } catch (refreshError: any) {
                processQueue(refreshError, null)
                isRefreshing = false
                useAuthStore.getState().logout()
                window.location.href = '/login'
                return Promise.reject(refreshError)
            }
        }

        return Promise.reject(error)
    }
)

export default api
