import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// استخدم Docker backend إذا كان متاح، وإلا استخدم المحلي
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:80'

export default defineConfig({
    plugins: [react()],
    server: {
        host: '127.0.0.1',
        port: 5173,
        proxy: {
            '/api': {
                target: apiProxyTarget,
                changeOrigin: true,
                secure: false
            },
        },
    },
})
