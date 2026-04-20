import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

// Use relative URL so Vite proxy handles it (no CORS issues)
const BASE_URL = '/api/v1'

const api = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Create a separate instance for retry requests to avoid interceptor loops
const retryApi = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Add request interceptor to retryApi to include Authorization header
retryApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

let isRefreshing = false
let failedQueue: any[] = []

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error)
        } else {
            prom.resolve(token)
        }
    })
    failedQueue = []
}

api.interceptors.request.use((config) => {
    // Always get fresh token from localStorage
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    } else {
        console.warn('No token found in localStorage')
    }
    return config
})

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config
        const requestUrl = originalRequest?.url || ''
        const isAuthEntryRequest =
            requestUrl.includes('/auth/login/') ||
            requestUrl.includes('/auth/register/')

        console.log('API Error:', error.response?.status, error.response?.data)

        if (error.response?.status === 401 && !originalRequest._retry && !isAuthEntryRequest) {
            console.log('Got 401 - attempting token refresh')

            if (isRefreshing) {
                console.log('Already refreshing - queuing request')
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject })
                }).then(token => {
                    originalRequest.headers.Authorization = `Bearer ${token}`
                    return retryApi(originalRequest)
                }).catch(err => {
                    return Promise.reject(err)
                })
            }

            originalRequest._retry = true
            isRefreshing = true

            const refreshToken = localStorage.getItem('refresh_token')
            console.log('Refresh token exists:', !!refreshToken)

            if (!refreshToken) {
                console.error('No refresh token available - logging out')
                isRefreshing = false
                useAuthStore.getState().logout()
                window.location.href = '/login'
                return Promise.reject(error)
            }

            try {
                console.log('Attempting to refresh token...')
                const response = await retryApi.post('/auth/token/refresh/', {
                    refresh: refreshToken
                })
                const newToken = response.data.access
                console.log('Token refreshed successfully')

                // Update store and localStorage
                useAuthStore.getState().setToken(newToken)
                localStorage.setItem('access_token', newToken)

                // Update original request with new token
                originalRequest.headers.Authorization = `Bearer ${newToken}`

                // Process queued requests
                processQueue(null, newToken)

                isRefreshing = false

                // Retry original request with new token using retryApi to avoid interceptor loop
                return retryApi(originalRequest)
            } catch (refreshError: any) {
                console.error('Token refresh failed:', refreshError.response?.data)
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
