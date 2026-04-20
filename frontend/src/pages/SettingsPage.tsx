import { useTranslation } from 'react-i18next'
import { User, Building2, Info } from 'lucide-react'
import DashboardLayout from '../components/Layout/DashboardLayout'
import { useAuthStore } from '../stores/authStore'

export default function SettingsPage() {
    const { t } = useTranslation()
    const { user } = useAuthStore()

    return (
        <DashboardLayout>
            <div className="space-y-8">
                <header>
                    <h1 className="text-3xl font-black text-gray-900">{t('settings.title')}</h1>
                    <p className="text-gray-500 mt-1">{t('settings.subtitle')}</p>
                </header>

                {/* Account Information */}
                <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-3 bg-primary-50 rounded-xl">
                            <User className="w-6 h-6 text-primary-600" />
                        </div>
                        <h2 className="text-xl font-bold text-gray-900">{t('settings.accountInfo')}</h2>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                {t('settings.username')}
                            </label>
                            <input
                                type="text"
                                name="username"
                                value={user?.username || ''}
                                disabled
                                data-testid="settings-username"
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl bg-gray-50 text-gray-600"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                {t('settings.email')}
                            </label>
                            <input
                                type="email"
                                name="email"
                                value={user?.email || ''}
                                disabled
                                data-testid="settings-email"
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl bg-gray-50 text-gray-600"
                            />
                        </div>
                    </div>
                </div>

                {/* Organization Information */}
                <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-3 bg-emerald-50 rounded-xl">
                            <Building2 className="w-6 h-6 text-emerald-600" />
                        </div>
                        <h2 className="text-xl font-bold text-gray-900">{t('settings.organizationInfo')}</h2>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                {t('settings.organizationName')}
                            </label>
                            <input
                                type="text"
                                name="tenant_name"
                                value={user?.tenant_name || ''}
                                disabled
                                data-testid="settings-tenant-name"
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl bg-gray-50 text-gray-600"
                            />
                        </div>
                    </div>

                    <div className="mt-6 p-4 bg-blue-50 border border-blue-100 rounded-xl flex gap-3">
                        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-blue-900">
                            <p className="font-medium">{t('settings.viewOnly')}</p>
                            <p className="mt-1 text-blue-700">{t('settings.contactSupport')}</p>
                        </div>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    )
}
