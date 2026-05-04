import { ReactNode, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
    Zap,
    Shield,
    BarChart,
    ChevronRight,
    Github,
    Twitter,
    Linkedin,
    FileText,
    MessageSquare,
    Brain,
    Building2,
    TrendingUp,
    Code,
    Upload,
    Cpu,
    Rocket,
    CheckCircle2,
} from 'lucide-react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'

type IconCard = {
    icon: ReactNode
    title: string
    description: string
    delay: number
}

export default function LandingPage() {
    const { t, i18n } = useTranslation()
    const { scrollY } = useScroll()
    const yA = useTransform(scrollY, [0, 800], [0, 180])
    const yB = useTransform(scrollY, [0, 800], [0, -130])
    const isArabic = i18n.language === 'ar'

    useEffect(() => {
        document.documentElement.dir = isArabic ? 'rtl' : 'ltr'
        document.documentElement.lang = i18n.language
    }, [isArabic, i18n.language])

    const heroChecklist = isArabic
        ? ['إجابات مبنية على وثائقك', 'ربط القنوات خلال دقائق', 'لوحة تحكم وتحليلات واضحة']
        : ['Answers grounded in your documents', 'Connect channels in minutes', 'Clear dashboard and analytics']

    const whyCards: IconCard[] = [
        { icon: <FileText className="w-7 h-7" />, title: t('landing.whyFeature1Title'), description: t('landing.whyFeature1Desc'), delay: 0.08 },
        { icon: <MessageSquare className="w-7 h-7" />, title: t('landing.whyFeature2Title'), description: t('landing.whyFeature2Desc'), delay: 0.14 },
        { icon: <Brain className="w-7 h-7" />, title: t('landing.whyFeature3Title'), description: t('landing.whyFeature3Desc'), delay: 0.2 },
        { icon: <Building2 className="w-7 h-7" />, title: t('landing.whyFeature4Title'), description: t('landing.whyFeature4Desc'), delay: 0.26 },
        { icon: <TrendingUp className="w-7 h-7" />, title: t('landing.whyFeature5Title'), description: t('landing.whyFeature5Desc'), delay: 0.32 },
        { icon: <Code className="w-7 h-7" />, title: t('landing.whyFeature6Title'), description: t('landing.whyFeature6Desc'), delay: 0.38 },
    ]

    const steps: IconCard[] = [
        { icon: <Upload className="w-9 h-9" />, title: t('landing.step1Title'), description: t('landing.step1Desc'), delay: 0.1 },
        { icon: <Cpu className="w-9 h-9" />, title: t('landing.step2Title'), description: t('landing.step2Desc'), delay: 0.18 },
        { icon: <Rocket className="w-9 h-9" />, title: t('landing.step3Title'), description: t('landing.step3Desc'), delay: 0.26 },
    ]

    return (
        <div className="min-h-screen text-slate-900 overflow-x-hidden selection:bg-blue-100 selection:text-blue-900">
            <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
                <motion.div
                    style={{ y: yA }}
                    className="absolute -top-24 -right-12 w-[390px] h-[390px] rounded-full blur-[105px] bg-blue-300/30 animate-float-pulse"
                />
                <motion.div
                    style={{ y: yB }}
                    className="absolute top-[28%] -left-12 w-[470px] h-[470px] rounded-full blur-[120px] bg-cyan-300/25 animate-float-pulse"
                />
                <div className="absolute inset-0 [background-image:linear-gradient(rgba(15,23,42,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.03)_1px,transparent_1px)] [background-size:36px_36px] opacity-40" />
            </div>

            <header className="fixed top-0 w-full z-50 px-4 sm:px-6 py-4">
                <nav className="container mx-auto">
                    <motion.div
                        initial={{ y: -24, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        className="surface-panel rounded-2xl px-4 py-3 sm:px-6 sm:py-4 flex items-center justify-between"
                    >
                        <div className="text-[1.4rem] sm:text-2xl font-extrabold tracking-tight bg-gradient-to-r from-blue-700 to-cyan-600 bg-clip-text text-transparent">
                            AI Chatbot
                        </div>

                        <div className="flex items-center gap-3 sm:gap-4">
                            <LanguageSwitcher />
                            <Link
                                to="/login"
                                data-testid="landing-login-link"
                                className="font-semibold text-slate-600 hover:text-blue-700 transition-colors"
                            >
                                {t('common.login')}
                            </Link>
                            <Link
                                to="/register"
                                data-testid="landing-register-link"
                                className="px-4 py-2 sm:px-6 sm:py-2.5 bg-blue-700 text-white rounded-xl font-semibold shadow-lg shadow-blue-200/70 hover:bg-blue-800 hover:-translate-y-0.5 transition-all"
                            >
                                {t('landing.getStarted')}
                            </Link>
                        </div>
                    </motion.div>
                </nav>
            </header>

            <section className="container mx-auto px-6 pt-40 pb-24 lg:pb-28">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 items-center">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.55 }}
                    >
                        <span className="inline-flex items-center rounded-full px-4 py-1.5 text-sm font-bold bg-blue-50 text-blue-700 border border-blue-100">
                            {t('landing.badge')}
                        </span>
                        <h1 className="headline-tight text-[2.3rem] sm:text-5xl lg:text-6xl font-extrabold leading-tight mt-6 mb-6">
                            {t('landing.heroTitle1')}
                            <br />
                            <span className="text-blue-700">{t('landing.heroTitle2')}</span>
                        </h1>
                        <p className="text-lg text-slate-600 leading-relaxed max-w-2xl mb-8">
                            {t('landing.heroDesc')}
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4">
                            <Link
                                to="/register"
                                data-testid="hero-register-link"
                                className="px-8 py-3.5 bg-slate-900 text-white rounded-2xl text-base sm:text-lg font-bold hover:bg-slate-800 transition-all flex items-center justify-center gap-2 shadow-xl"
                            >
                                {t('landing.startFree')} <ChevronRight className="w-5 h-5" />
                            </Link>
                            <button className="px-8 py-3.5 bg-white text-slate-700 border-2 border-slate-200 rounded-2xl text-base sm:text-lg font-bold hover:border-blue-200 transition-all">
                                {t('landing.watchDemo')}
                            </button>
                        </div>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 24 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.65, delay: 0.1 }}
                        className="relative"
                    >
                        <div className="surface-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden">
                            <div className="absolute -inset-x-20 top-0 h-12 bg-gradient-to-r from-transparent via-white/70 to-transparent animate-shimmer-slide" />
                            <h3 className="text-xl sm:text-2xl font-extrabold headline-tight mb-6">
                                {isArabic ? 'منصة واحدة لرحلة العميل كاملة' : 'One Platform For Your Support Workflow'}
                            </h3>
                            <div className="space-y-3">
                                {heroChecklist.map((item, idx) => (
                                    <motion.div
                                        key={item}
                                        initial={{ opacity: 0, x: isArabic ? 20 : -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: 0.25 + idx * 0.1, duration: 0.4 }}
                                        className="flex items-start gap-3 rounded-xl border border-slate-100 bg-white p-3.5"
                                    >
                                        <CheckCircle2 className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                                        <span className="font-semibold text-slate-700">{item}</span>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            <section className="container mx-auto px-6 py-14">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <FeatureCard delay={0.1} icon={<Zap className="w-7 h-7" />} title={t('landing.feature1Title')} description={t('landing.feature1Desc')} tone="from-blue-600 to-cyan-500" />
                    <FeatureCard delay={0.18} icon={<Shield className="w-7 h-7" />} title={t('landing.feature2Title')} description={t('landing.feature2Desc')} tone="from-teal-600 to-cyan-500" />
                    <FeatureCard delay={0.26} icon={<BarChart className="w-7 h-7" />} title={t('landing.feature3Title')} description={t('landing.feature3Desc')} tone="from-slate-700 to-slate-900" />
                </div>
            </section>

            <section className="container mx-auto px-6 py-20">
                <div className="surface-panel rounded-[2rem] p-8 md:p-12">
                    <motion.div
                        initial={{ opacity: 0, y: 14 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.55 }}
                        viewport={{ once: true, amount: 0.2 }}
                        className="text-center mb-12"
                    >
                        <h2 className="headline-tight text-4xl md:text-5xl font-extrabold mb-3">
                            {t('landing.whyBuildTitle')}
                        </h2>
                        <p className="text-lg text-slate-600 max-w-3xl mx-auto">
                            {t('landing.whyBuildSubtitle')}
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        {whyCards.map((card) => (
                            <WhyFeatureCard key={card.title} {...card} />
                        ))}
                    </div>
                </div>
            </section>

            <section className="container mx-auto px-6 py-20">
                <motion.div
                    initial={{ opacity: 0, y: 14 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    viewport={{ once: true, amount: 0.2 }}
                    className="text-center mb-12"
                >
                    <h2 className="headline-tight text-4xl md:text-5xl font-extrabold mb-3">
                        {t('landing.howItWorksTitle')}
                    </h2>
                    <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                        {t('landing.howItWorksSubtitle')}
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-7">
                    {steps.map((step, idx) => (
                        <HowItWorksStep
                            key={step.title}
                            step={`${idx + 1}`}
                            icon={step.icon}
                            title={step.title}
                            description={step.description}
                            delay={step.delay}
                        />
                    ))}
                </div>
            </section>

            <section className="container mx-auto px-6 pb-20">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.55 }}
                    viewport={{ once: true, amount: 0.2 }}
                    className="surface-panel rounded-[2.1rem] p-8 md:p-12 text-center relative overflow-hidden"
                >
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-100/30 via-transparent to-cyan-100/30" />
                    <div className="relative">
                        <h3 className="headline-tight text-3xl md:text-5xl font-extrabold mb-4">
                            {isArabic ? 'حوّل محتواك إلى تجربة دعم أسرع وأكثر دقة' : 'Turn Your Content Into Faster, Smarter Support'}
                        </h3>
                        <p className="text-lg text-slate-600 max-w-3xl mx-auto mb-8">
                            {isArabic
                                ? 'ابدأ بتجهيز وثائقك، اربط القنوات المناسبة، وامنح فريقك والعملاء تجربة محادثة تعتمد على معلوماتك الحقيقية.'
                                : 'Start with your documents, connect the channels you already use, and deliver grounded answers to customers and teams.'}
                        </p>
                        <Link
                            to="/register"
                            className="inline-flex items-center justify-center gap-2 px-9 py-3.5 bg-blue-700 text-white rounded-2xl text-lg font-bold hover:bg-blue-800 transition-all"
                        >
                            {t('landing.getStarted')} <ChevronRight className="w-5 h-5" />
                        </Link>
                    </div>
                </motion.div>
            </section>

            <footer className="bg-white/70 border-t border-white px-6 pt-14 pb-8">
                <div className="container mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-10">
                        <div className="col-span-1 md:col-span-2">
                            <div className="text-2xl font-extrabold text-blue-700 mb-5">AI Chatbot</div>
                            <p className="text-slate-600 max-w-md leading-relaxed">
                                {t('landing.footerDesc')}
                            </p>
                        </div>
                        <div>
                            <h4 className="font-bold text-slate-900 mb-4">{t('landing.quickLinks')}</h4>
                            <ul className="space-y-3 text-slate-600 font-medium">
                                <li><a href="#" className="hover:text-blue-700 transition-colors">{t('landing.home')}</a></li>
                                <li><a href="#" className="hover:text-blue-700 transition-colors">{t('landing.features')}</a></li>
                                <li><a href="#" className="hover:text-blue-700 transition-colors">{t('landing.pricing')}</a></li>
                            </ul>
                        </div>
                        <div className="flex flex-col gap-5">
                            <h4 className="font-bold text-slate-900">{t('landing.followUs')}</h4>
                            <div className="flex items-center gap-3">
                                <SocialIcon icon={<Twitter size={18} />} />
                                <SocialIcon icon={<Linkedin size={18} />} />
                                <SocialIcon icon={<Github size={18} />} />
                            </div>
                        </div>
                    </div>

                    <div className="border-t border-slate-200 pt-6 flex flex-col md:flex-row items-center justify-between gap-3">
                        <p className="text-slate-500 font-medium">
                            © {new Date().getFullYear()} AI Chatbot. {t('landing.allRights')}
                        </p>
                        <div className="flex items-center gap-4 text-sm text-slate-500">
                            <a href="#" className="hover:text-slate-700">{t('landing.privacy')}</a>
                            <span>•</span>
                            <a href="#" className="hover:text-slate-700">{t('landing.terms')}</a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    )
}

function FeatureCard({
    icon,
    title,
    description,
    delay,
    tone,
}: {
    icon: ReactNode
    title: string
    description: string
    delay: number
    tone: string
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay }}
            viewport={{ once: true, amount: 0.2 }}
            whileHover={{ y: -8 }}
            className="surface-panel rounded-3xl p-7 relative overflow-hidden"
        >
            <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${tone} text-white flex items-center justify-center mb-5 shadow-lg`}>
                {icon}
            </div>
            <h3 className="text-xl font-extrabold mb-2">{title}</h3>
            <p className="text-slate-600 leading-relaxed">{description}</p>
        </motion.div>
    )
}

function WhyFeatureCard({ icon, title, description, delay }: IconCard) {
    return (
        <motion.article
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay }}
            viewport={{ once: true, amount: 0.2 }}
            whileHover={{ y: -5 }}
            className="bg-white rounded-2xl border border-slate-200/80 p-6 text-center shadow-[0_12px_30px_-25px_rgba(15,23,42,0.5)]"
        >
            <div className="w-16 h-16 rounded-full mx-auto mb-5 bg-blue-50 text-blue-700 flex items-center justify-center">
                {icon}
            </div>
            <h3 className="text-2xl font-extrabold headline-tight mb-3">{title}</h3>
            <p className="text-slate-600 leading-relaxed">{description}</p>
        </motion.article>
    )
}

function HowItWorksStep({
    step,
    icon,
    title,
    description,
    delay,
}: {
    step: string
    icon: ReactNode
    title: string
    description: string
    delay: number
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            viewport={{ once: true, amount: 0.25 }}
            className="surface-panel rounded-3xl p-7 relative"
        >
            <div className="absolute top-4 right-4 text-sm font-extrabold text-blue-700/80 bg-blue-50 px-2.5 py-1 rounded-lg">
                {step}
            </div>
            <div className="w-16 h-16 rounded-[1.15rem] bg-slate-100 text-blue-700 flex items-center justify-center mb-6">
                {icon}
            </div>
            <h3 className="text-2xl font-extrabold headline-tight mb-3">{title}</h3>
            <p className="text-slate-600 leading-relaxed">{description}</p>
        </motion.div>
    )
}

function SocialIcon({ icon }: { icon: ReactNode }) {
    return (
        <a
            href="#"
            className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-blue-700 hover:border-blue-200 transition-colors"
        >
            {icon}
        </a>
    )
}
