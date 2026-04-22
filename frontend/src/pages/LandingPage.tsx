import { Link } from 'react-router-dom'
import { Zap, Shield, BarChart, ChevronRight, Github, Twitter, Linkedin, FileText, MessageSquare, Brain, Building2, TrendingUp, Code, Upload, Cpu, Rocket } from 'lucide-react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useEffect } from 'react'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function LandingPage() {
    const { t, i18n } = useTranslation()
    const { scrollY } = useScroll()
    const y1 = useTransform(scrollY, [0, 500], [0, 200])
    const y2 = useTransform(scrollY, [0, 500], [0, -150])

    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr'
        document.documentElement.lang = i18n.language
    }, [i18n.language])

    return (
        <div className="min-h-screen bg-gradient-to-br from-primary-50 to-white text-gray-900 overflow-x-hidden selection:bg-primary-100 selection:text-primary-900">

            {/* Animated Background */}
            <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
                <motion.div
                    style={{ y: y1 }}
                    animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.4, 0.3] }}
                    transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                    className="absolute -top-[5%] -right-[5%] w-[400px] h-[400px] bg-blue-100/60 rounded-full blur-[100px]"
                />
                <motion.div
                    style={{ y: y2 }}
                    animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0.3, 0.2] }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    className="absolute top-[30%] -left-[5%] w-[500px] h-[500px] bg-cyan-100/50 rounded-full blur-[110px]"
                />
            </div>

            {/* Header */}
            <header className="fixed top-0 w-full z-50 px-6 py-4">
                <nav className="container mx-auto">
                    <motion.div
                        initial={{ y: -20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        className="flex items-center justify-between backdrop-blur-md bg-white/70 p-4 rounded-2xl border border-gray-100 shadow-sm"
                    >
                        <div className="text-2xl font-black bg-gradient-to-r from-primary-600 to-cyan-600 bg-clip-text text-transparent">
                            AI Chatbot
                        </div>

                        <div className="flex items-center gap-4">
                            <LanguageSwitcher />
                            <Link to="/login" data-testid="landing-login-link" className="font-medium text-gray-600 hover:text-primary-600 transition-colors">
                                {t('common.login')}
                            </Link>
                            <Link to="/register" data-testid="landing-register-link" className="px-6 py-2.5 bg-primary-600 text-white rounded-xl font-semibold shadow-lg shadow-primary-200 hover:bg-primary-700 hover:-translate-y-0.5 transition-all">
                                {t('landing.getStarted')}
                            </Link>
                        </div>
                    </motion.div>
                </nav>
            </header>

            {/* Hero Section */}
            <section className="container mx-auto px-6 pt-40 pb-32 text-center">
                <motion.div
                    initial="hidden"
                    animate="visible"
                    variants={{
                        hidden: { opacity: 0 },
                        visible: { opacity: 1, transition: { staggerChildren: 0.2 } }
                    }}
                >
                    <motion.span
                        variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                        className="px-4 py-1.5 rounded-full bg-primary-50 text-primary-700 text-sm font-bold mb-6 inline-block border border-primary-100"
                    >
                        {t('landing.badge')}
                    </motion.span>

                    <motion.h1
                        variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                        className="text-5xl md:text-7xl font-black text-gray-900 mb-8 leading-[1.15]"
                    >
                        {t('landing.heroTitle1')} <br />
                        <span className="text-primary-600">{t('landing.heroTitle2')}</span>
                    </motion.h1>

                    <motion.p
                        variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                        className="text-xl text-gray-600 max-w-2xl mx-auto mb-12 leading-relaxed"
                    >
                        {t('landing.heroDesc')}
                    </motion.p>

                    <motion.div
                        variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                        className="flex flex-col sm:flex-row gap-4 justify-center"
                    >
                        <Link to="/register" data-testid="hero-register-link" className="px-10 py-4 bg-gray-900 text-white rounded-2xl text-lg font-bold hover:bg-gray-800 transition-all flex items-center justify-center gap-2 shadow-xl">
                            {t('landing.startFree')} <ChevronRight className="w-5 h-5" />
                        </Link>
                        <button className="px-10 py-4 bg-white text-gray-700 border-2 border-gray-100 rounded-2xl text-lg font-bold hover:border-primary-200 transition-all">
                            {t('landing.watchDemo')}
                        </button>
                    </motion.div>
                </motion.div>
            </section>

            {/* Features Section */}
            <section className="container mx-auto px-6 py-20">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <FeatureCard delay={0.1} icon={<Zap className="w-8 h-8" />} title={t('landing.feature1Title')} description={t('landing.feature1Desc')} color="bg-primary-600" />
                    <FeatureCard delay={0.2} icon={<Shield className="w-8 h-8" />} title={t('landing.feature2Title')} description={t('landing.feature2Desc')} color="bg-cyan-600" />
                    <FeatureCard delay={0.3} icon={<BarChart className="w-8 h-8" />} title={t('landing.feature3Title')} description={t('landing.feature3Desc')} color="bg-gray-900" />
                </div>
            </section>

            {/* Why Build Chatbot Section */}
            <section className="container mx-auto px-6 py-20 bg-gradient-to-b from-white to-primary-50/30">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <h2 className="text-4xl md:text-5xl font-black text-gray-900 mb-4">
                        {t('landing.whyBuildTitle')}
                    </h2>
                    <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                        {t('landing.whyBuildSubtitle')}
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <WhyFeatureCard
                        delay={0.1}
                        icon={<FileText className="w-7 h-7" />}
                        title={t('landing.whyFeature1Title')}
                        description={t('landing.whyFeature1Desc')}
                        gradient="from-blue-500 to-cyan-500"
                    />
                    <WhyFeatureCard
                        delay={0.2}
                        icon={<MessageSquare className="w-7 h-7" />}
                        title={t('landing.whyFeature2Title')}
                        description={t('landing.whyFeature2Desc')}
                        gradient="from-purple-500 to-pink-500"
                    />
                    <WhyFeatureCard
                        delay={0.3}
                        icon={<Brain className="w-7 h-7" />}
                        title={t('landing.whyFeature3Title')}
                        description={t('landing.whyFeature3Desc')}
                        gradient="from-green-500 to-emerald-500"
                    />
                    <WhyFeatureCard
                        delay={0.4}
                        icon={<Building2 className="w-7 h-7" />}
                        title={t('landing.whyFeature4Title')}
                        description={t('landing.whyFeature4Desc')}
                        gradient="from-orange-500 to-red-500"
                    />
                    <WhyFeatureCard
                        delay={0.5}
                        icon={<TrendingUp className="w-7 h-7" />}
                        title={t('landing.whyFeature5Title')}
                        description={t('landing.whyFeature5Desc')}
                        gradient="from-indigo-500 to-blue-500"
                    />
                    <WhyFeatureCard
                        delay={0.6}
                        icon={<Code className="w-7 h-7" />}
                        title={t('landing.whyFeature6Title')}
                        description={t('landing.whyFeature6Desc')}
                        gradient="from-yellow-500 to-orange-500"
                    />
                </div>
            </section>

            {/* How It Works Section */}
            <section className="container mx-auto px-6 py-20">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <h2 className="text-4xl md:text-5xl font-black text-gray-900 mb-4">
                        {t('landing.howItWorksTitle')}
                    </h2>
                    <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                        {t('landing.howItWorksSubtitle')}
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                    <HowItWorksStep
                        delay={0.1}
                        step="1"
                        icon={<Upload className="w-10 h-10" />}
                        title={t('landing.step1Title')}
                        description={t('landing.step1Desc')}
                    />
                    <HowItWorksStep
                        delay={0.2}
                        step="2"
                        icon={<Cpu className="w-10 h-10" />}
                        title={t('landing.step2Title')}
                        description={t('landing.step2Desc')}
                    />
                    <HowItWorksStep
                        delay={0.3}
                        step="3"
                        icon={<Rocket className="w-10 h-10" />}
                        title={t('landing.step3Title')}
                        description={t('landing.step3Desc')}
                    />
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-gray-50 border-t border-gray-100 pt-16 pb-8 px-6">
                <div className="container mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
                        <div className="col-span-1 md:col-span-2">
                            <div className="text-2xl font-black text-primary-600 mb-6">AI Chatbot</div>
                            <p className="text-gray-500 max-w-sm leading-relaxed">
                                {t('landing.footerDesc')}
                            </p>
                        </div>
                        <div>
                            <h4 className="font-bold text-gray-900 mb-6">{t('landing.quickLinks')}</h4>
                            <ul className="space-y-4 text-gray-600 font-medium">
                                <li><a href="#" className="hover:text-primary-600 transition-colors">{t('landing.home')}</a></li>
                                <li><a href="#" className="hover:text-primary-600 transition-colors">{t('landing.features')}</a></li>
                                <li><a href="#" className="hover:text-primary-600 transition-colors">{t('landing.pricing')}</a></li>
                            </ul>
                        </div>
                        <div className="flex flex-col gap-6">
                            <h4 className="font-bold text-gray-900">{t('landing.followUs')}</h4>
                            <div className="flex items-center gap-4">
                                <SocialIcon icon={<Twitter size={20} />} />
                                <SocialIcon icon={<Linkedin size={20} />} />
                                <SocialIcon icon={<Github size={20} />} />
                            </div>
                        </div>
                    </div>

                    <div className="border-t border-gray-200 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
                        <p className="text-gray-500 font-medium">
                            © {new Date().getFullYear()} AI Chatbot. {t('landing.allRights')}
                        </p>
                        <div className="flex items-center gap-4 text-sm text-gray-400">
                            <a href="#" className="hover:text-gray-600">{t('landing.privacy')}</a>
                            <span>•</span>
                            <a href="#" className="hover:text-gray-600">{t('landing.terms')}</a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    )
}

function FeatureCard({ icon, title, description, delay, color }: any) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            viewport={{ once: true }}
            whileHover={{ y: -8, transition: { duration: 0.2 } }}
            className="p-8 bg-white rounded-3xl border border-gray-100 hover:border-primary-200 hover:shadow-2xl hover:shadow-primary-100/20 transition-all group relative overflow-hidden"
        >
            <div className={`w-14 h-14 ${color} rounded-2xl flex items-center justify-center text-white mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
                {icon}
            </div>
            <h3 className="text-xl font-bold mb-3">{title}</h3>
            <p className="text-gray-500 leading-relaxed">{description}</p>
            <div className="absolute -bottom-2 -left-2 w-24 h-24 bg-primary-50/50 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
        </motion.div>
    )
}

function WhyFeatureCard({ icon, title, description, delay, gradient }: any) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay }}
            viewport={{ once: true }}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className="p-6 bg-white rounded-2xl border border-gray-100 hover:border-gray-200 hover:shadow-xl transition-all group cursor-pointer"
        >
            <div className={`w-12 h-12 bg-gradient-to-br ${gradient} rounded-xl flex items-center justify-center text-white mb-4 group-hover:scale-110 transition-transform duration-300`}>
                {icon}
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
            <p className="text-gray-600 text-sm leading-relaxed">{description}</p>
        </motion.div>
    )
}

function HowItWorksStep({ step, icon, title, description, delay }: any) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay }}
            viewport={{ once: true }}
            className="relative"
        >
            <motion.div
                whileHover={{ scale: 1.05 }}
                transition={{ duration: 0.3 }}
                className="bg-white rounded-2xl p-8 border-2 border-gray-100 hover:border-primary-200 hover:shadow-xl transition-all group cursor-pointer"
            >
                {/* Step Number Badge */}
                <div className="absolute -top-4 -left-4 w-12 h-12 bg-gradient-to-br from-primary-600 to-cyan-600 rounded-full flex items-center justify-center text-white font-black text-xl shadow-lg">
                    {step}
                </div>

                {/* Icon */}
                <div className="w-16 h-16 bg-gradient-to-br from-primary-50 to-cyan-50 rounded-2xl flex items-center justify-center text-primary-600 mb-6 group-hover:scale-110 transition-transform duration-300">
                    {icon}
                </div>

                {/* Content */}
                <h3 className="text-xl font-bold text-gray-900 mb-3">{title}</h3>
                <p className="text-gray-600 leading-relaxed">{description}</p>
            </motion.div>
        </motion.div>
    )
}

function SocialIcon({ icon }: { icon: React.ReactNode }) {
    return (
        <a href="#" className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-400 hover:text-primary-600 hover:border-primary-200 hover:shadow-sm transition-all">
            {icon}
        </a>
    )
}
