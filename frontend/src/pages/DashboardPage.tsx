import { useQuery } from 'react-query'
import { useTranslation } from 'react-i18next'
import { FileText, MessageSquare, Users, TrendingUp, ArrowUpRight, Sparkles, Zap, Target } from 'lucide-react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import DashboardLayout from '../components/Layout/DashboardLayout'
import api from '../services/api'

export default function DashboardPage() {
    const { t } = useTranslation()
    const { data: stats } = useQuery('dashboard-stats', async () => {
        const response = await api.get('/analytics/dashboard/')
        return response.data
    })

    const quickActions = [
        {
            title: t('dashboard.uploadDocument'),
            description: t('dashboard.uploadDocumentDesc'),
            icon: FileText,
            color: 'from-blue-500 to-cyan-500',
            link: '/documents',
            iconBg: 'bg-blue-50',
            iconColor: 'text-blue-600'
        },
        {
            title: t('dashboard.tryChat'),
            description: t('dashboard.tryChatDesc'),
            icon: MessageSquare,
            color: 'from-purple-500 to-pink-500',
            link: '/chat',
            iconBg: 'bg-purple-50',
            iconColor: 'text-purple-600'
        },
        {
            title: t('dashboard.connectChannels'),
            description: t('dashboard.connectChannelsDesc'),
            icon: Users,
            color: 'from-emerald-500 to-teal-500',
            link: '/channels',
            iconBg: 'bg-emerald-50',
            iconColor: 'text-emerald-600'
        },
    ]

    const statCards = [
        {
            label: t('dashboard.documents'),
            value: stats?.documents?.total || 0,
            change: '+12%',
            icon: FileText,
            gradient: 'from-violet-500 to-purple-500',
            bgGradient: 'from-violet-50 to-purple-50'
        },
        {
            label: t('dashboard.sessions'),
            value: stats?.sessions?.total || 0,
            change: '+8%',
            icon: MessageSquare,
            gradient: 'from-blue-500 to-cyan-500',
            bgGradient: 'from-blue-50 to-cyan-50'
        },
        {
            label: t('dashboard.queries'),
            value: stats?.queries?.total || 0,
            change: '+23%',
            icon: TrendingUp,
            gradient: 'from-emerald-500 to-teal-500',
            bgGradient: 'from-emerald-50 to-teal-50'
        },
    ]

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Hero Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative overflow-hidden bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 rounded-3xl p-8 md:p-12 text-white"
                >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
                    <div className="absolute bottom-0 left-0 w-96 h-96 bg-white/5 rounded-full blur-3xl"></div>

                    <div className="relative z-10">
                        <div className="flex items-center gap-2 mb-4">
                            <Sparkles className="w-6 h-6" />
                            <span className="text-sm font-semibold uppercase tracking-wider opacity-90">
                                {t('dashboard.title')}
                            </span>
                        </div>
                        <h1 className="text-4xl md:text-5xl font-black mb-4">
                            {t('dashboard.subtitle')}
                        </h1>
                        <p className="text-lg opacity-90 max-w-2xl">
                            Harness the power of AI to transform your documents into intelligent conversations
                        </p>
                    </div>
                </motion.div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {statCards.map((stat, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className={`relative overflow-hidden bg-gradient-to-br ${stat.bgGradient} rounded-2xl p-6 border border-gray-100`}
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className={`p-3 rounded-xl bg-gradient-to-br ${stat.gradient} text-white shadow-lg`}>
                                    <stat.icon className="w-6 h-6" />
                                </div>
                                <div className="flex items-center gap-1 text-emerald-600 text-sm font-bold">
                                    <ArrowUpRight className="w-4 h-4" />
                                    {stat.change}
                                </div>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-gray-600 mb-1">{stat.label}</p>
                                <h3 className="text-4xl font-black text-gray-900">{stat.value}</h3>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Quick Actions */}
                <div>
                    <div className="flex items-center gap-3 mb-6">
                        <Zap className="w-6 h-6 text-primary-600" />
                        <h2 className="text-2xl font-black text-gray-900">{t('dashboard.quickStart')}</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {quickActions.map((action, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.3 + i * 0.1 }}
                                whileHover={{ scale: 1.02, y: -4 }}
                                className="group"
                            >
                                <Link
                                    to={action.link}
                                    className="block relative overflow-hidden bg-white rounded-2xl p-6 border-2 border-gray-100 hover:border-primary-200 transition-all shadow-sm hover:shadow-xl"
                                >
                                    <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${action.color} opacity-0 group-hover:opacity-10 blur-2xl transition-opacity`}></div>

                                    <div className="relative z-10">
                                        <div className={`inline-flex p-3 rounded-xl ${action.iconBg} mb-4 group-hover:scale-110 transition-transform`}>
                                            <action.icon className={`w-6 h-6 ${action.iconColor}`} />
                                        </div>
                                        <h3 className="text-lg font-bold text-gray-900 mb-2 group-hover:text-primary-600 transition-colors">
                                            {action.title}
                                        </h3>
                                        <p className="text-sm text-gray-600 leading-relaxed">
                                            {action.description}
                                        </p>
                                        <div className="mt-4 flex items-center gap-2 text-primary-600 font-semibold text-sm opacity-0 group-hover:opacity-100 transition-opacity">
                                            Get Started
                                            <ArrowUpRight className="w-4 h-4" />
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="bg-white rounded-2xl border border-gray-100 p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Target className="w-6 h-6 text-primary-600" />
                        <h2 className="text-2xl font-black text-gray-900">{t('dashboard.recentActivity')}</h2>
                    </div>
                    <div className="text-center py-12">
                        <div className="inline-flex p-4 rounded-full bg-gray-50 mb-4">
                            <MessageSquare className="w-8 h-8 text-gray-400" />
                        </div>
                        <p className="text-gray-500">{t('dashboard.noActivity')}</p>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    )
}
