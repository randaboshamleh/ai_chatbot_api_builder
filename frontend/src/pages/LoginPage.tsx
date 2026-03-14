import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authService } from '../services/authService'
import { useAuthStore } from '../stores/authStore'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function LoginPage() {
    const navigate = useNavigate()
    const { login } = useAuthStore()
    const { t, i18n } = useTranslation()
    const [formData, setFormData] = useState({ username: '', password: '' })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr'
        document.documentElement.lang = i18n.language
    }, [i18n.language])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const response = await authService.login(formData)
            console.log('Login response:', response)
            console.log('Access token:', response.access)
            console.log('Refresh token:', response.refresh)
            login(response.access, response.user, response.refresh)
            console.log('Token saved to localStorage:', localStorage.getItem('access_token'))
            navigate('/dashboard')
        } catch (err: any) {
            setError(err.response?.data?.error || t('auth.loginError'))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-primary-50 to-white flex items-center justify-center p-4">
            <div className="absolute top-4 right-4">
                <LanguageSwitcher />
            </div>
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">{t('auth.welcomeBack')}</h1>
                    <p className="text-gray-600">{t('auth.loginSubtitle')}</p>
                </div>

                <div className="bg-white rounded-2xl shadow-xl p-8">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {error && (
                            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                                {error}
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                {t('auth.email')}
                            </label>
                            <input
                                type="text"
                                required
                                value={formData.username}
                                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                placeholder="username"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                {t('auth.password')}
                            </label>
                            <input
                                type="password"
                                required
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                placeholder="••••••••"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                        >
                            {loading ? t('auth.loggingIn') : t('common.login')}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-gray-600">
                            {t('auth.noAccount')}{' '}
                            <Link to="/register" className="text-primary-600 hover:text-primary-700 font-medium">
                                {t('auth.registerNow')}
                            </Link>
                        </p>
                    </div>
                </div>

                <div className="mt-6 text-center">
                    <Link to="/" className="text-gray-600 hover:text-gray-900">
                        {i18n.language === 'ar' ? '← ' : '→ '}{t('auth.backToHome')}
                    </Link>
                </div>
            </div>
        </div>
    )
}