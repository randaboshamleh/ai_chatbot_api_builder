import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authService } from '../services/authService'
import { useAuthStore } from '../stores/authStore'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function RegisterPage() {
    const navigate = useNavigate()
    const { login } = useAuthStore()
    const { t, i18n } = useTranslation()
    const [formData, setFormData] = useState({
        tenant_name: '',
        subdomain: '',
        email: '',
        password: '',
        confirmPassword: '',
        first_name: '',
        last_name: '',
    })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr'
        document.documentElement.lang = i18n.language
    }, [i18n.language])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match')
            return
        }

        setLoading(true)

        try {
            const backendData = {
                company_name: formData.tenant_name,
                slug: formData.subdomain,
                username: formData.email.split('@')[0],
                email: formData.email,
                password: formData.password,
            }

            const response = await authService.register(backendData)
            login(response.access, response.user, response.refresh)
            navigate('/dashboard')
        } catch (err: any) {
            const errorMessage = err.response?.data?.error
                || err.response?.data?.detail
                || err.response?.data?.message
                || Object.values(err.response?.data || {}).flat().join(', ')
                || t('auth.registerError')
            setError(errorMessage)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-primary-50 to-white flex items-center justify-center p-4">
            <div className="absolute top-4 right-4">
                <LanguageSwitcher />
            </div>
            <div className="w-full max-w-2xl">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">{t('auth.createAccount')}</h1>
                    <p className="text-gray-600">{t('auth.registerSubtitle')}</p>
                </div>

                <div className="bg-white rounded-2xl shadow-xl p-8">
                    <form onSubmit={handleSubmit} className="space-y-6" data-testid="register-form">
                        {error && (
                            <div
                                data-testid="auth-error"
                                className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm"
                            >
                                {error}
                            </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    {t('auth.firstName')}
                                </label>
                                <input
                                    type="text"
                                    name="first_name"
                                    required
                                    value={formData.first_name}
                                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                    data-testid="register-first-name"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    {t('auth.lastName')}
                                </label>
                                <input
                                    type="text"
                                    name="last_name"
                                    required
                                    value={formData.last_name}
                                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                    data-testid="register-last-name"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                {t('auth.email')}
                            </label>
                            <input
                                type="email"
                                name="email"
                                required
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                data-testid="register-email"
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                placeholder="example@company.com"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    {t('auth.password')}
                                </label>
                                <input
                                    type="password"
                                    name="password"
                                    required
                                    minLength={8}
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    data-testid="register-password"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    placeholder="********"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Confirm Password
                                </label>
                                <input
                                    type="password"
                                    name="confirmPassword"
                                    required
                                    minLength={8}
                                    value={formData.confirmPassword}
                                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                                    data-testid="register-confirm-password"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    placeholder="********"
                                />
                            </div>
                        </div>

                        <div className="border-t pt-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">{t('auth.organizationInfo')}</h3>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        {t('auth.organizationName')}
                                    </label>
                                    <input
                                        type="text"
                                        name="tenant_name"
                                        required
                                        value={formData.tenant_name}
                                        onChange={(e) => setFormData({ ...formData, tenant_name: e.target.value })}
                                        data-testid="register-tenant-name"
                                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        {t('auth.subdomain')}
                                    </label>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="text"
                                            name="subdomain"
                                            required
                                            value={formData.subdomain}
                                            onChange={(e) => setFormData({ ...formData, subdomain: e.target.value.toLowerCase() })}
                                            data-testid="register-subdomain"
                                            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                            placeholder="company"
                                        />
                                        <span className="text-gray-500">.chatbot.com</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            data-testid="register-submit"
                            className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                        >
                            {loading ? t('auth.creating') : t('auth.createAccountBtn')}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-gray-600">
                            {t('auth.haveAccount')}{' '}
                            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium" data-testid="go-login-link">
                                {t('auth.signIn')}
                            </Link>
                        </p>
                    </div>
                </div>

                <div className="mt-6 text-center">
                    <Link to="/" className="text-gray-600 hover:text-gray-900" data-testid="back-home-link">
                        {t('auth.backToHome')}
                    </Link>
                </div>
            </div>
        </div>
    )
}
