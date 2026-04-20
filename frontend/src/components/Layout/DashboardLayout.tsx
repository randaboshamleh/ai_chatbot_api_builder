import { ReactNode, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
    LayoutDashboard,
    FileText,
    MessageSquare,
    BarChart3,
    Settings,
    Radio,
    LogOut,
    Sparkles
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import LanguageSwitcher from '../LanguageSwitcher'

interface DashboardLayoutProps {
    children: ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const location = useLocation()
    const navigate = useNavigate()
    const { user, logout } = useAuthStore()
    const { t, i18n } = useTranslation()

    const navigation = [
        { name: t('nav.dashboard'), href: '/dashboard', icon: LayoutDashboard },
        { name: t('nav.documents'), href: '/documents', icon: FileText },
        { name: t('nav.chat'), href: '/chat', icon: MessageSquare },
        { name: t('nav.analytics'), href: '/analytics', icon: BarChart3 },
        { name: t('nav.channels'), href: '/channels', icon: Radio },
        { name: t('nav.settings'), href: '/settings', icon: Settings },
    ]

    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr'
        document.documentElement.lang = i18n.language
    }, [i18n.language])

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <div className="min-h-screen relative overflow-hidden">
            {/* Animated Background Orbs */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
                <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
                <div className="absolute bottom-0 left-1/3 w-96 h-96 bg-sky-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
            </div>

            {/* Sidebar */}
            <div className={`fixed inset-y-0 ${i18n.language === 'ar' ? 'right-0' : 'left-0'} w-64 glass-effect z-50`}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="flex items-center justify-center h-16 border-b border-white/20">
                        <div className="flex items-center gap-2">
                            <div className="p-2 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <h1 className="text-xl font-black bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                                AI Chatbot
                            </h1>
                        </div>
                    </div>

                    {/* User Info */}
                    <div className="p-4 border-b border-white/20">
                        <div className="flex items-center space-x-3 space-x-reverse">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
                                <span className="text-white font-bold text-sm">
                                    {user?.username?.[0]?.toUpperCase() || 'U'}
                                </span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold text-gray-900 truncate">
                                    {user?.username}
                                </p>
                                <p className="text-xs text-gray-600 truncate">{user?.tenant_name}</p>
                            </div>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    data-testid={`nav-${item.href.replace('/', '')}`}
                                    className={`flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all ${isActive
                                        ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg'
                                        : 'text-gray-700 hover:bg-white/50'
                                        }`}
                                >
                                    <item.icon className={`w-5 h-5 ${i18n.language === 'ar' ? 'ml-3' : 'mr-3'}`} />
                                    {item.name}
                                </Link>
                            )
                        })}
                    </nav>

                    {/* Language & Logout */}
                    <div className="p-4 border-t border-white/20 space-y-2">
                        <LanguageSwitcher />
                        <button
                            onClick={handleLogout}
                            data-testid="logout-button"
                            className="flex items-center w-full px-4 py-3 text-sm font-semibold text-red-600 rounded-xl hover:bg-red-50 transition-all"
                        >
                            <LogOut className={`w-5 h-5 ${i18n.language === 'ar' ? 'ml-3' : 'mr-3'}`} />
                            {t('common.logout')}
                        </button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className={`${i18n.language === 'ar' ? 'mr-64' : 'ml-64'} relative z-10`}>
                <main className="p-8">{children}</main>
            </div>

            <style>{`
                @keyframes blob {
                    0% {
                        transform: translate(0px, 0px) scale(1);
                    }
                    33% {
                        transform: translate(30px, -50px) scale(1.1);
                    }
                    66% {
                        transform: translate(-20px, 20px) scale(0.9);
                    }
                    100% {
                        transform: translate(0px, 0px) scale(1);
                    }
                }
                .animate-blob {
                    animation: blob 7s infinite;
                }
                .animation-delay-2000 {
                    animation-delay: 2s;
                }
                .animation-delay-4000 {
                    animation-delay: 4s;
                }
            `}</style>
        </div>
    )
}
