import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
    id: string
    username: string
    email: string
    role: string
    tenant_name: string
}

interface AuthState {
    user: User | null
    token: string | null
    refreshToken: string | null
    isAuthenticated: boolean
    login: (token: string, user: User, refreshToken?: string) => void
    logout: () => void
    updateUser: (user: User) => void
    setToken: (token: string) => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            login: (token, user, refreshToken) => {
                set({ token, user, refreshToken, isAuthenticated: true })
                localStorage.setItem('access_token', token)
                if (refreshToken) {
                    localStorage.setItem('refresh_token', refreshToken)
                }
            },
            logout: () => {
                set({ token: null, user: null, refreshToken: null, isAuthenticated: false })
                localStorage.removeItem('access_token')
                localStorage.removeItem('refresh_token')
            },
            updateUser: (user) => set({ user }),
            setToken: (token) => {
                set({ token })
                localStorage.setItem('access_token', token)
            },
        }),
        {
            name: 'auth-storage',
        }
    )
)
