import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useTranslation } from 'react-i18next'
import {
    Send, CheckCircle, XCircle, Copy,
    ExternalLink, Loader2, ArrowRight, Zap, Link as LinkIcon, AlertTriangle, Globe, FileText, BarChart, MessageSquare
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import DashboardLayout from '../components/Layout/DashboardLayout'
import api from '../services/api'

const fetchChannels = async () => (await api.get('/tenant/channels/')).data
const fetchProfile = async () => (await api.get('/tenant/profile/')).data

const fetchBotInfo = async (token: string) => {
    const res = await fetch(`https://api.telegram.org/bot${token}/getMe`)
    const data = await res.json()
    if (data.ok) return data.result
    throw new Error(data.description || 'Invalid token')
}

const isLocalhost = () =>
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

type Step = 'idle' | 'input' | 'connecting' | 'done'

export default function ChannelsPage() {
    const { t, i18n } = useTranslation()
    const qc = useQueryClient()
    const isArabic = i18n.language === 'ar'

    // Telegram state
    const [tgStep, setTgStep] = useState<Step>('idle')
    const [tgToken, setTgToken] = useState('')
    const [tgError, setTgError] = useState('')
    const [tgBotUsername, setTgBotUsername] = useState('')
    const [tgCopied, setTgCopied] = useState(false)

    // Web Chat state
    const [webCopied, setWebCopied] = useState(false)

    // Shared ngrok
    const [ngrokUrl, setNgrokUrl] = useState('')

    const { data: channels = [] } = useQuery('channels', fetchChannels, {
        onSuccess: (data: any[]) => {
            const tg = data.find((c: any) => c.channel_type === 'telegram')
            if (tg?.is_active) setTgStep('done')
        }
    })
    const { data: profile } = useQuery('profile', fetchProfile)
    const tenantId = profile?.id
    const tenantSubdomain = profile?.subdomain || 'default-company'

    const baseUrl = isLocalhost() ? (ngrokUrl.trim() || 'http://localhost:80') : window.location.origin
    const webChatDemoUrl = `${window.location.origin}/webchat-demo`

    // Check if web channel exists
    const webChannel = (channels as any[]).find((c: any) => c.channel_type === 'web')
    const isWebActive = webChannel?.is_active || false

    // Telegram connect
    const tgMutation = useMutation(
        async ({ token, webhookBase }: { token: string; webhookBase: string }) => {
            const botInfo = await fetchBotInfo(token)
            setTgBotUsername(botInfo.username)
            const payload: any = { channel_type: 'telegram', telegram_token: token, is_active: true, input_mode: 'text' }
            if (webhookBase) payload.webhook_base_url = webhookBase
            const existing = (channels as any[]).find((c: any) => c.channel_type === 'telegram')
            const res = existing ? await api.patch('/tenant/channels/', payload) : await api.post('/tenant/channels/', payload)
            if (res.data.webhook_error) throw new Error(`Webhook: ${res.data.webhook_error}`)
            return botInfo.username
        },
        {
            onSuccess: () => { setTgStep('done'); setTgError(''); qc.invalidateQueries('channels') },
            onError: (e: any) => { setTgError(e.message || t('channels.saveError')); setTgStep('input') }
        }
    )

    const handleTgConnect = () => {
        if (!tgToken.trim()) return
        if (isLocalhost() && !ngrokUrl.trim()) { setTgError(t('channels.ngrokRequired')); return }
        setTgError(''); setTgStep('connecting')
        tgMutation.mutate({ token: tgToken.trim(), webhookBase: ngrokUrl.trim() })
    }

    const handleTgDisconnect = async () => {
        try { await api.patch('/tenant/channels/', { channel_type: 'telegram', is_active: false }); setTgStep('idle'); setTgToken(''); setTgBotUsername(''); qc.invalidateQueries('channels') } catch { }
    }

    const botLink = tgBotUsername ? `https://t.me/${tgBotUsername}` : ''
    const channelsSubtitle = isArabic
        ? 'اربط قنواتك المتاحة الآن (Telegram و Web Chat) ليوصل البوت إجابات موحدة مبنية على وثائقك.'
        : 'Connect your available channels (Telegram and Web Chat) so customers get consistent answers grounded in your documents.'

    const valueCards = isArabic
        ? [
            { icon: <MessageSquare className="w-6 h-6" />, title: 'وصول مباشر للعملاء', description: 'استقبل رسائل العملاء من تيليجرام أو موقعك بنفس جودة الرد.' },
            { icon: <FileText className="w-6 h-6" />, title: 'إجابات من نفس المعرفة', description: 'كل قناة تعتمد على نفس قاعدة الوثائق المرفوعة داخل النظام.' },
            { icon: <BarChart className="w-6 h-6" />, title: 'رؤية أوضح للأداء', description: 'تتبّع التفاعل والاستفسارات من القنوات في لوحة التحليلات.' },
        ]
        : [
            { icon: <MessageSquare className="w-6 h-6" />, title: 'Meet Customers Where They Chat', description: 'Handle questions from Telegram and your website with one assistant behavior.' },
            { icon: <FileText className="w-6 h-6" />, title: 'One Knowledge Across Channels', description: 'Every channel answers from the same uploaded documents and indexed content.' },
            { icon: <BarChart className="w-6 h-6" />, title: 'Cleaner Performance Visibility', description: 'Track conversations and channel impact from your analytics dashboard.' },
        ]

    const quickFlow = isArabic
        ? [
            { label: '1', title: 'جهّز المحتوى', desc: 'ارفع الوثائق حتى تكون الإجابات مستندة لمعلوماتك الفعلية.' },
            { label: '2', title: 'اربط القناة', desc: 'أدخل توكن تيليجرام أو استخدم كود الدمج لـ Web Chat.' },
            { label: '3', title: 'ابدأ واستقبل الرسائل', desc: 'شارك رابط البوت أو فعّل الودجت داخل موقعك مباشرة.' },
        ]
        : [
            { label: '1', title: 'Prepare Knowledge', desc: 'Upload your documents so answers are grounded in your actual content.' },
            { label: '2', title: 'Connect A Channel', desc: 'Use Telegram token setup or embed the Web Chat script.' },
            { label: '3', title: 'Go Live Fast', desc: 'Share your bot link or publish the website widget right away.' },
        ]

    return (
        <DashboardLayout>
            <div className="max-w-6xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-primary-500 to-cyan-500 rounded-2xl shadow-lg">
                        <LinkIcon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black text-gray-900">{t('channels.title')}</h1>
                        <p className="text-gray-600 mt-1">{channelsSubtitle}</p>
                    </div>
                </div>

                <motion.section
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.45 }}
                    className="surface-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden"
                >
                    <div className="absolute -inset-x-20 top-0 h-12 bg-gradient-to-r from-transparent via-white/70 to-transparent animate-shimmer-slide" />
                    <div className="relative">
                        <h2 className="headline-tight text-2xl sm:text-3xl font-black text-gray-900">
                            {isArabic ? 'ليش إعداد القنوات مهم؟' : 'Why Channel Setup Matters'}
                        </h2>
                        <p className="text-gray-600 mt-2 max-w-3xl">
                            {isArabic
                                ? 'ربط القنوات يخلي تجربة العميل ثابتة، ويضمن أن نفس منطق الإجابة يوصل في تيليجرام وموقعك بدون تكرار إعدادات.'
                                : 'Connecting channels keeps your support experience consistent, so the same answer quality is delivered in Telegram and your website.'}
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                            {valueCards.map((card, idx) => (
                                <motion.div
                                    key={card.title}
                                    initial={{ opacity: 0, y: 14 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.1 + idx * 0.09, duration: 0.35 }}
                                    whileHover={{ y: -5 }}
                                    className="bg-white rounded-2xl border border-slate-200 p-5 shadow-[0_12px_30px_-24px_rgba(15,23,42,0.35)]"
                                >
                                    <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center mb-3">
                                        {card.icon}
                                    </div>
                                    <h3 className="text-lg font-extrabold text-gray-900 mb-1">{card.title}</h3>
                                    <p className="text-sm text-gray-600 leading-relaxed">{card.description}</p>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </motion.section>

                {/* Shared ngrok field for localhost */}
                {isLocalhost() && tgStep === 'input' && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 bg-amber-50 border-2 border-amber-200 rounded-2xl space-y-2">
                        <div className="flex items-center gap-2 text-amber-700 font-semibold">
                            <AlertTriangle className="w-4 h-4" />
                            {t('channels.localDevMode')}
                        </div>
                        <p className="text-xs text-amber-600">{t('channels.ngrokHint')}</p>
                        <input type="text" value={ngrokUrl} onChange={e => setNgrokUrl(e.target.value)}
                            placeholder="https://xxxx.ngrok-free.app"
                            className="w-full px-3 py-2.5 border border-amber-300 rounded-lg bg-white text-sm font-mono focus:border-amber-500 outline-none"
                        />
                    </motion.div>
                )}

                {/* Cards Grid - Telegram and Web Chat side by side */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* ── TELEGRAM CARD ── */}
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl border-2 border-gray-100 shadow-sm overflow-hidden">
                        <div className="bg-gradient-to-br from-blue-50 to-cyan-50 p-6 border-b border-gray-100 flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 text-white shadow-lg"><Send className="w-6 h-6" /></div>
                                <div>
                                    <h3 className="text-xl font-bold text-gray-900">Telegram</h3>
                                    <p className="text-sm text-gray-500">{t('channels.telegramDesc')}</p>
                                </div>
                            </div>
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold ${tgStep === 'done' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                                {tgStep === 'done' ? <><CheckCircle className="w-4 h-4" />{t('channels.active')}</> : <><XCircle className="w-4 h-4" />{t('channels.inactive')}</>}
                            </div>
                        </div>
                        <div className="p-6">
                            <AnimatePresence mode="wait">
                                {tgStep === 'idle' && (
                                    <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">
                                        <p className="text-gray-500 text-sm mb-6">{t('channels.telegramConnectHint')}</p>
                                        <button onClick={() => setTgStep('input')} data-testid="telegram-start-connect" className="w-full py-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-bold text-lg flex items-center justify-center gap-3 hover:shadow-lg transition-all">
                                            <Send className="w-5 h-5" />{t('channels.connectTelegram')}<ArrowRight className="w-5 h-5" />
                                        </button>
                                        <div className="mt-5 text-xs text-gray-400 space-y-2 border-t pt-4">
                                            <p className="font-semibold text-gray-500 mb-2">Setup:</p>
                                            <p>1. {t('channels.step1')}</p>
                                            <p>2. {t('channels.step2')}</p>
                                            <p>3. {t('channels.step3')}</p>
                                        </div>
                                        {/* Spacer to match Web Chat height */}
                                        <div className="h-20"></div>
                                    </motion.div>
                                )}
                                {tgStep === 'input' && (
                                    <motion.div key="input" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="space-y-4">
                                        <div className="text-center">
                                            <p className="text-lg font-bold text-gray-800">{t('channels.pasteToken')}</p>
                                            <p className="text-sm text-gray-500 mt-1">{t('channels.pasteTokenHint')}</p>
                                        </div>
                                        <input autoFocus type="text" value={tgToken}
                                            data-testid="telegram-token-input"
                                            onChange={e => { setTgToken(e.target.value); setTgError('') }}
                                            onKeyDown={e => e.key === 'Enter' && handleTgConnect()}
                                            placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                                            className="w-full px-4 py-4 border-2 border-blue-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none font-mono text-sm"
                                        />
                                        {tgError && <p className="text-red-500 text-sm flex items-center gap-2"><XCircle className="w-4 h-4" />{tgError}</p>}
                                        <div className="flex gap-3">
                                            <button onClick={() => { setTgStep('idle'); setTgError('') }} className="flex-1 py-3 border-2 border-gray-200 text-gray-600 rounded-xl font-semibold hover:bg-gray-50">{t('common.cancel')}</button>
                                            <button onClick={handleTgConnect} disabled={!tgToken.trim()} data-testid="telegram-connect-submit" className="flex-grow py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:shadow-lg disabled:opacity-50">
                                                <Zap className="w-5 h-5" />{t('channels.connectNow')}
                                            </button>
                                        </div>
                                    </motion.div>
                                )}
                                {tgStep === 'connecting' && (
                                    <motion.div key="connecting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center py-8 gap-4">
                                        <Loader2 className="w-12 h-12 animate-spin text-blue-500" />
                                        <p className="text-gray-600 font-semibold">{t('channels.connecting')}</p>
                                        <p className="text-gray-400 text-sm">{t('channels.connectingHint')}</p>
                                    </motion.div>
                                )}
                                {tgStep === 'done' && (
                                    <motion.div key="done" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="space-y-5">
                                        <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                                            <CheckCircle className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                                            <div>
                                                <p className="font-bold text-emerald-800">{t('channels.connected')}</p>
                                                <p className="text-sm text-emerald-600">{t('channels.webhookAutoSet')}</p>
                                            </div>
                                        </div>
                                        {botLink && (
                                            <div>
                                                <p className="text-sm font-semibold text-gray-700 mb-2">{t('channels.shareBotLink')}</p>
                                                <div className="flex gap-2">
                                                    <div className="flex-1 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl font-mono text-sm text-blue-700 truncate">{botLink}</div>
                                                    <button onClick={() => { navigator.clipboard.writeText(botLink); setTgCopied(true); setTimeout(() => setTgCopied(false), 2000) }} className="px-3 py-2 bg-blue-100 hover:bg-blue-200 rounded-xl">
                                                        {tgCopied ? <CheckCircle className="w-5 h-5 text-emerald-600" /> : <Copy className="w-5 h-5 text-blue-600" />}
                                                    </button>
                                                    <a href={botLink} target="_blank" rel="noopener noreferrer" className="px-3 py-2 bg-blue-100 hover:bg-blue-200 rounded-xl"><ExternalLink className="w-5 h-5 text-blue-600" /></a>
                                                </div>
                                            </div>
                                        )}
                                        <button onClick={handleTgDisconnect} className="w-full py-2.5 border-2 border-red-200 text-red-500 rounded-xl text-sm font-semibold hover:bg-red-50">{t('channels.disconnect')}</button>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>

                    {/* ── WEB CHAT CARD ── */}
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white rounded-2xl border-2 border-gray-100 shadow-sm overflow-hidden">
                        <div className="bg-gradient-to-br from-sky-50 to-blue-50 p-6 border-b border-gray-100 flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="p-3 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 text-white shadow-lg"><Globe className="w-6 h-6" /></div>
                                <div>
                                    <h3 className="text-xl font-bold text-gray-900">Web Chat</h3>
                                    <p className="text-sm text-gray-500">{t('channels.webChatDesc')}</p>
                                </div>
                            </div>
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold ${isWebActive ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                                {isWebActive ? <><CheckCircle className="w-4 h-4" />{t('channels.active')}</> : <><XCircle className="w-4 h-4" />{t('channels.inactive')}</>}
                            </div>
                        </div>
                        <div className="p-6">
                            {isWebActive ? (
                                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-5">
                                    <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                                        <CheckCircle className="w-6 h-6 text-blue-600 flex-shrink-0" />
                                        <div>
                                            <p className="font-bold text-blue-800">{t('channels.webChatActive')}</p>
                                            <p className="text-sm text-blue-600">{t('channels.webChatActiveDesc')}</p>
                                        </div>
                                    </div>

                                    {/* Integration Code */}
                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">{t('channels.integrationCode')}</p>
                                        <div className="bg-gray-900 rounded-xl p-4 overflow-x-auto">
                                            <pre className="text-xs text-gray-100 font-mono whitespace-pre-wrap">
                                                {`<!-- Add this code before </body> on your website -->
<script src="${window.location.origin}/webchat.js"></script>
<script>
  WebChat.init({
    tenantSlug: '${tenantSubdomain}',
    position: 'bottom-right',
    primaryColor: '#2563EB'
  });
</script>`}
                                            </pre>
                                        </div>
                                        <button
                                            onClick={() => {
                                                const code = `<!-- Add this code before </body> on your website -->\n<script src="${window.location.origin}/webchat.js"></script>\n<script>\n  WebChat.init({\n    tenantSlug: '${tenantSubdomain}',\n    position: 'bottom-right',\n    primaryColor: '#2563EB'\n  });\n</script>`;
                                                navigator.clipboard.writeText(code);
                                                setWebCopied(true);
                                                setTimeout(() => setWebCopied(false), 2000);
                                            }}
                                            className="mt-2 w-full py-2 px-4 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg text-sm font-semibold flex items-center justify-center gap-2"
                                        >
                                            {webCopied ? <><CheckCircle className="w-4 h-4" />{t('common.copied')}</> : <><Copy className="w-4 h-4" />{t('common.copyCode')}</>}
                                        </button>
                                    </div>

                                    {/* Demo Link */}
                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">{t('channels.tryDemo')}</p>
                                        <a
                                            href={webChatDemoUrl}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center justify-center gap-2 w-full py-3 bg-gradient-to-r from-sky-500 to-blue-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all"
                                        >
                                            <ExternalLink className="w-5 h-5" />
                                            {t('channels.openDemo')}
                                        </a>
                                    </div>
                                </motion.div>
                            ) : (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                    <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl mb-4">
                                        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                                        <p className="text-sm text-amber-700">{t('channels.webChatNotActive')}</p>
                                    </div>
                                    <p className="text-gray-500 text-sm mb-4">{t('channels.webChatContactAdmin')}</p>
                                </motion.div>
                            )}
                        </div>
                    </motion.div>
                </div>
                {/* End of grid */}

                <motion.section
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.12, duration: 0.4 }}
                    className="surface-panel rounded-3xl p-6 sm:p-8"
                >
                    <h2 className="headline-tight text-2xl sm:text-3xl font-black text-gray-900 mb-2">
                        {isArabic ? 'كيف تفعّل القنوات بسرعة' : 'How To Activate Channels Quickly'}
                    </h2>
                    <p className="text-gray-600 mb-6">
                        {isArabic
                            ? 'الخطوات التالية تعطيك مسار واضح بدون تعقيد: جهّز المعرفة، اربط القناة، وابدأ التفاعل.'
                            : 'Use this short flow to go live without friction: prepare knowledge, connect a channel, and start conversations.'}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {quickFlow.map((step, idx) => (
                            <motion.div
                                key={step.title}
                                initial={{ opacity: 0, y: 14 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.18 + idx * 0.08, duration: 0.35 }}
                                whileHover={{ y: -4 }}
                                className="bg-white rounded-2xl border border-slate-200 p-5"
                            >
                                <div className="w-9 h-9 rounded-lg bg-blue-700 text-white font-extrabold flex items-center justify-center mb-3">
                                    {step.label}
                                </div>
                                <h3 className="text-lg font-extrabold text-gray-900 mb-1">{step.title}</h3>
                                <p className="text-sm text-gray-600 leading-relaxed">{step.desc}</p>
                            </motion.div>
                        ))}
                    </div>
                </motion.section>

            </div>
        </DashboardLayout>
    )
}
