import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Send, MessageCircle, CheckCircle, XCircle, Zap, Link as LinkIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import DashboardLayout from '../components/Layout/DashboardLayout'

export default function ChannelsPage() {
    const { t } = useTranslation()
    const [telegramConfig, setTelegramConfig] = useState({
        botToken: '',
        webhookUrl: '',
        active: false
    })
    const [whatsappConfig, setWhatsappConfig] = useState({
        phoneNumber: '',
        apiKey: '',
        active: false
    })

    const channels: Array<{
        name: string
        icon: React.ElementType
        gradient: string
        bgGradient: string
        description: string
        config: Record<string, string | boolean>
        setConfig: (v: any) => void
        fields: Array<{ key: string; label: string; type: string; placeholder: string }>
    }> = [
            {
                name: t('channels.telegram'),
                icon: Send,
                gradient: 'from-blue-500 to-cyan-500',
                bgGradient: 'from-blue-50 to-cyan-50',
                description: 'Connect your Telegram bot to enable automated responses',
                config: telegramConfig,
                setConfig: setTelegramConfig,
                fields: [
                    { key: 'botToken', label: t('channels.botToken'), type: 'text', placeholder: '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz' },
                    { key: 'webhookUrl', label: t('channels.webhookUrl'), type: 'text', placeholder: 'https://your-domain.com/webhook' }
                ]
            },
            {
                name: t('channels.whatsapp'),
                icon: MessageCircle,
                gradient: 'from-emerald-500 to-teal-500',
                bgGradient: 'from-emerald-50 to-teal-50',
                description: 'Integrate WhatsApp Business API for customer support',
                config: whatsappConfig,
                setConfig: setWhatsappConfig,
                fields: [
                    { key: 'phoneNumber', label: t('channels.phoneNumber'), type: 'text', placeholder: '+1234567890' },
                    { key: 'apiKey', label: t('channels.apiKey'), type: 'password', placeholder: 'Your WhatsApp API Key' }
                ]
            }
        ]

    const handleSave = (channelConfig: any, setConfig: any) => {
        setConfig({ ...channelConfig, active: true })
        // Here you would typically make an API call to save the configuration
    }

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-2xl shadow-lg">
                        <LinkIcon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black text-gray-900">{t('channels.title')}</h1>
                        <p className="text-gray-600 mt-1">{t('channels.subtitle')}</p>
                    </div>
                </div>

                {/* Active Channels Overview */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gradient-to-br from-primary-50 via-purple-50 to-pink-50 rounded-2xl p-6 border-2 border-primary-100"
                >
                    <div className="flex items-center gap-3 mb-4">
                        <Zap className="w-5 h-5 text-primary-600" />
                        <h2 className="text-lg font-bold text-gray-900">{t('channels.activeChannels')}</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {channels.map((channel, i) => (
                            <div key={i} className="flex items-center justify-between bg-white rounded-xl p-4 border border-gray-200">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg bg-gradient-to-br ${channel.gradient} text-white`}>
                                        <channel.icon className="w-5 h-5" />
                                    </div>
                                    <span className="font-semibold text-gray-900">{channel.name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    {channel.config.active ? (
                                        <>
                                            <CheckCircle className="w-5 h-5 text-emerald-600" />
                                            <span className="text-sm font-semibold text-emerald-600">{t('channels.active')}</span>
                                        </>
                                    ) : (
                                        <>
                                            <XCircle className="w-5 h-5 text-gray-400" />
                                            <span className="text-sm font-semibold text-gray-400">{t('channels.inactive')}</span>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* Channel Configuration Cards */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {channels.map((channel, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className="bg-white rounded-2xl border-2 border-gray-100 overflow-hidden shadow-sm hover:shadow-lg transition-all"
                        >
                            {/* Card Header */}
                            <div className={`bg-gradient-to-br ${channel.bgGradient} p-6 border-b border-gray-100`}>
                                <div className="flex items-center gap-4 mb-3">
                                    <div className={`p-3 rounded-xl bg-gradient-to-br ${channel.gradient} text-white shadow-lg`}>
                                        <channel.icon className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold text-gray-900">{channel.name}</h3>
                                        <p className="text-sm text-gray-600 mt-1">{channel.description}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Card Body */}
                            <div className="p-6 space-y-4">
                                {channel.fields.map((field, idx) => (
                                    <div key={idx}>
                                        <label className="block text-sm font-semibold text-gray-700 mb-2">
                                            {field.label}
                                        </label>
                                        <input
                                            type={field.type}
                                            value={channel.config[field.key] as string}
                                            onChange={(e) => channel.setConfig({
                                                ...channel.config,
                                                [field.key]: e.target.value
                                            })}
                                            placeholder={field.placeholder}
                                            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all outline-none"
                                        />
                                    </div>
                                ))}

                                <button
                                    onClick={() => handleSave(channel.config, channel.setConfig)}
                                    className={`w-full py-3 bg-gradient-to-r ${channel.gradient} text-white rounded-xl hover:shadow-lg transition-all font-semibold flex items-center justify-center gap-2`}
                                >
                                    <CheckCircle className="w-5 h-5" />
                                    {t('channels.saveSettings')}
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Info Section */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="bg-blue-50 border-2 border-blue-100 rounded-2xl p-6"
                >
                    <div className="flex gap-4">
                        <div className="flex-shrink-0">
                            <div className="p-3 bg-blue-100 rounded-xl">
                                <LinkIcon className="w-6 h-6 text-blue-600" />
                            </div>
                        </div>
                        <div>
                            <h3 className="font-bold text-gray-900 mb-2">Integration Guide</h3>
                            <p className="text-sm text-gray-600 leading-relaxed mb-3">
                                Connect your messaging channels to enable automated AI-powered responses. Make sure to configure webhooks properly for real-time message handling.
                            </p>
                            <ul className="text-sm text-gray-600 space-y-1">
                                <li className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                                    Telegram: Create a bot via @BotFather and get your token
                                </li>
                                <li className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                                    WhatsApp: Register for WhatsApp Business API access
                                </li>
                                <li className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                                    Configure webhooks to receive incoming messages
                                </li>
                            </ul>
                        </div>
                    </div>
                </motion.div>
            </div>
        </DashboardLayout>
    )
}
