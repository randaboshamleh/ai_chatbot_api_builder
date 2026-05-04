import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Default to direct Django API in dev to avoid nginx 502 issues.
// Override with VITE_API_PROXY_TARGET when needed.
const normalizeProxyTarget = (value: string) =>
    value.replace('http://127.0.0.1:8000', 'http://localhost:8000')

const apiProxyTarget = normalizeProxyTarget(process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000')

export default defineConfig({
    plugins: [react()],
    server: {
        host: '127.0.0.1',
        port: 5173,
        proxy: {
            '/api': {
                target: apiProxyTarget,
                changeOrigin: true,
                secure: false,
            },
        },
    },
})
