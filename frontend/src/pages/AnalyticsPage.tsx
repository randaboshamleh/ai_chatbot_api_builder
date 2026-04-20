import { useQuery } from 'react-query'
import { BarChart3, TrendingUp, Clock, MessageSquare, ArrowDownRight, ArrowUpRight, Zap, Activity, ShieldAlert } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import DashboardLayout from '../components/Layout/DashboardLayout'
import api from '../services/api'
import { formatDate } from '../utils/formatters'
import { useAuthStore } from '../stores/authStore'

export default function AnalyticsPage() {
    const { t, i18n } = useTranslation()
    const { user } = useAuthStore()
    const hasTenantWorkspace = Boolean(user?.tenant_name)

    const { data: analytics, isError } = useQuery(['analytics', user?.id], async () => {
        const response = await api.get('/analytics/queries/')
        return response.data
    }, {
        enabled: hasTenantWorkspace,
        retry: (failureCount, error: any) => {
            const status = error?.response?.status
            if (status === 401 || status === 403) {
                return false
            }
            return failureCount < 2
        },
    })

    const tenantAlertTitle = i18n.language === 'ar'
        ? 'الحساب غير مرتبط بمساحة شركة'
        : 'Account is not linked to a tenant workspace'
    const tenantAlertDescription = i18n.language === 'ar'
        ? 'هذا الحساب لا يملك tenant، لذلك لا يمكن تحميل صفحة الإحصائيات.'
        : 'This user has no tenant, so the analytics page cannot be loaded.'
    const loadErrorTitle = i18n.language === 'ar'
        ? 'تعذّر تحميل بيانات الإحصائيات'
        : 'Unable to load analytics data'

    const stats = [
        {
            title: t('analytics.totalQueries'),
            value: analytics?.total_queries || 0,
            icon: MessageSquare,
            gradient: 'from-blue-500 to-cyan-500',
            bgGradient: 'from-blue-50 to-cyan-50',
            trend: '+12%',
            trendUp: true
        },
        {
            title: t('analytics.avgResponseTime'),
            value: `${analytics?.avg_response_time?.toFixed(2) || 0}s`,
            icon: Clock,
            gradient: 'from-amber-500 to-orange-500',
            bgGradient: 'from-amber-50 to-orange-50',
            trend: '-5%',
            trendUp: false
        },
        {
            title: t('analytics.successRate'),
            value: `${analytics?.success_rate || 0}%`,
            icon: TrendingUp,
            gradient: 'from-emerald-500 to-teal-500',
            bgGradient: 'from-emerald-50 to-teal-50',
            trend: '+2%',
            trendUp: true
        },
    ]

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-2xl shadow-lg">
                        <Activity className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black text-gray-900">{t('analytics.title')}</h1>
                        <p className="text-gray-600 mt-1">{t('analytics.subtitle')}</p>
                    </div>
                </div>

                {!hasTenantWorkspace && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
                        <div className="flex items-start gap-3">
                            <ShieldAlert className="w-5 h-5 mt-0.5" />
                            <div>
                                <p className="font-bold">{tenantAlertTitle}</p>
                                <p className="text-sm mt-1">{tenantAlertDescription}</p>
                            </div>
                        </div>
                    </div>
                )}

                {hasTenantWorkspace && isError && (
                    <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800">
                        <p className="font-semibold">{loadErrorTitle}</p>
                    </div>
                )}

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {stats.map((stat, i) => (
                        <motion.div
                            key={i}
                            data-testid="analytics-stat-card"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className={`relative overflow-hidden bg-gradient-to-br ${stat.bgGradient} rounded-2xl p-6 border-2 border-gray-100`}
                        >
                            <div className="absolute top-0 right-0 w-32 h-32 bg-white/50 rounded-full blur-2xl"></div>

                            <div className="relative z-10">
                                <div className="flex justify-between items-start mb-6">
                                    <div className={`p-3 rounded-xl bg-gradient-to-br ${stat.gradient} text-white shadow-lg`}>
                                        <stat.icon className="w-6 h-6" />
                                    </div>
                                    <div className={`flex items-center gap-1 text-sm font-bold px-3 py-1 rounded-full ${stat.trendUp
                                        ? 'text-emerald-700 bg-emerald-100'
                                        : 'text-red-700 bg-red-100'
                                        }`}>
                                        {stat.trendUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                                        {stat.trend}
                                    </div>
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-gray-600 mb-2">{stat.title}</p>
                                    <h3 className="text-4xl font-black text-gray-900">{stat.value}</h3>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Queries Table */}
                <motion.div
                    data-testid="analytics-recent-queries"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-white rounded-2xl border-2 border-gray-100 overflow-hidden shadow-sm"
                >
                    <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center bg-gradient-to-r from-gray-50 to-white">
                        <div className="flex items-center gap-3">
                            <Zap className="w-5 h-5 text-primary-600" />
                            <h2 className="font-black text-gray-900 text-lg">{t('analytics.recentQueries')}</h2>
                        </div>
                        <button className="text-sm text-primary-600 font-bold hover:text-primary-700 transition-colors px-4 py-2 rounded-lg hover:bg-primary-50">
                            {t('analytics.exportData')}
                        </button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                                    <th className="px-6 py-4 text-left font-bold">{t('analytics.query')}</th>
                                    <th className="px-6 py-4 text-left font-bold">{t('analytics.smartAnswer')}</th>
                                    <th className="px-6 py-4 text-center font-bold">{t('analytics.speed')}</th>
                                    <th className="px-6 py-4 text-left font-bold">{t('analytics.date')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {analytics?.recent_queries?.length > 0 ? (
                                    analytics.recent_queries.map((query: any, idx: number) => (
                                        <motion.tr
                                            key={query.id}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="hover:bg-primary-50/30 transition-colors group"
                                        >
                                            <td className="px-6 py-4 text-sm font-semibold text-gray-900 max-w-[250px]">
                                                <div className="truncate group-hover:text-primary-600 transition-colors">
                                                    {query.query}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 max-w-[350px]">
                                                <div className="truncate">
                                                    {query.answer}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-center">
                                                <span className="inline-flex items-center px-3 py-1 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-full font-mono text-xs font-bold text-emerald-700">
                                                    {query.response_time?.toFixed(2)}s
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                {formatDate(query.created_at)}
                                            </td>
                                        </motion.tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center">
                                            <div className="inline-flex p-4 rounded-full bg-gray-50 mb-3">
                                                <BarChart3 className="w-8 h-8 text-gray-400" />
                                            </div>
                                            <p className="text-gray-500 font-medium">{t('analytics.noQueries')}</p>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            </div>
        </DashboardLayout>
    )
}
