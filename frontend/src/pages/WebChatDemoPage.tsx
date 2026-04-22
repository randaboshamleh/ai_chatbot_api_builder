import WebChatWidget from '../components/WebChatWidget';
import { motion } from 'framer-motion';
import { MessageSquare, Zap, Shield, Globe, CheckCircle } from 'lucide-react';

export default function WebChatDemoPage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8" dir="ltr">
            <div className="max-w-6xl mx-auto">
                {/* Hero Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="bg-white rounded-2xl shadow-xl p-8 mb-8"
                >
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                            <MessageSquare className="w-6 h-6 text-white" />
                        </div>
                        <h1 className="text-4xl font-bold text-gray-800 text-left">
                            Web Chat Widget Demo
                        </h1>
                    </div>
                    <p className="text-gray-600 text-lg mb-6 text-left">
                        Experience our AI-powered chat widget in action. Click the chat button in the bottom right corner to start chatting!
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FeatureItem icon={<Zap />} text="Real-time AI responses" />
                        <FeatureItem icon={<Shield />} text="Secure & private conversations" />
                        <FeatureItem icon={<Globe />} text="Multi-language support" />
                        <FeatureItem icon={<CheckCircle />} text="Source citations included" />
                    </div>
                </motion.div>

                {/* Why Use Web Chat Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6"
                >
                    <BenefitCard
                        title="24/7 Availability"
                        description="Your chatbot never sleeps. Provide instant support to customers around the clock."
                        gradient="from-blue-500 to-cyan-500"
                        delay={0.1}
                    />
                    <BenefitCard
                        title="Easy Integration"
                        description="Add to any website with just 2 lines of code. No complex setup required."
                        gradient="from-purple-500 to-pink-500"
                        delay={0.2}
                    />
                    <BenefitCard
                        title="Smart Answers"
                        description="RAG-powered responses with citations from your uploaded documents."
                        gradient="from-green-500 to-emerald-500"
                        delay={0.3}
                    />
                </motion.div>
            </div>

            {/* Web Chat Widget */}
            <WebChatWidget
                tenantSlug="spu"
                position="bottom-right"
                primaryColor="#3B82F6"
            />
        </div>
    );
}

function FeatureItem({ icon, text }: { icon: React.ReactNode; text: string }) {
    return (
        <div className="flex items-center gap-3 text-left">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600 flex-shrink-0">
                {icon}
            </div>
            <span className="text-gray-700 font-medium">{text}</span>
        </div>
    );
}

function BenefitCard({ title, description, gradient, delay }: any) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay }}
            whileHover={{ y: -5, scale: 1.02 }}
            className="bg-white rounded-xl p-6 shadow-lg hover:shadow-2xl transition-all cursor-pointer"
        >
            <div className={`w-12 h-12 bg-gradient-to-br ${gradient} rounded-xl mb-4 flex items-center justify-center`}>
                <div className="w-6 h-6 bg-white/30 rounded-full" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2 text-left">{title}</h3>
            <p className="text-gray-600 text-left leading-relaxed">{description}</p>
        </motion.div>
    );
}
