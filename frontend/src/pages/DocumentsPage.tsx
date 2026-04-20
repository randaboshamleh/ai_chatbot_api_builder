import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useTranslation } from 'react-i18next'
import { Upload, FileText, Trash2, CheckCircle, Clock, AlertCircle, Loader2, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import DashboardLayout from '../components/Layout/DashboardLayout'
import { documentService } from '../services/documentService'

export default function DocumentsPage() {
    const { t } = useTranslation()
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const queryClient = useQueryClient()

    const { data: documents, isLoading } = useQuery('documents', documentService.list)

    const uploadMutation = useMutation(documentService.upload, {
        onSuccess: () => {
            queryClient.invalidateQueries('documents')
            setSelectedFile(null)
        },
    })

    const deleteMutation = useMutation(documentService.delete, {
        onSuccess: () => {
            queryClient.invalidateQueries('documents')
        },
    })

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0])
        }
    }

    const handleUpload = () => {
        if (selectedFile) {
            uploadMutation.mutate(selectedFile)
        }
    }

    const getStatusConfig = (status: string) => {
        switch (status) {
            case 'indexed':
                return {
                    icon: CheckCircle,
                    label: t('documents.status.indexed'),
                    color: 'text-emerald-600',
                    bg: 'bg-emerald-50',
                    border: 'border-emerald-200'
                }
            case 'processing':
                return {
                    icon: Loader2,
                    label: t('documents.status.processing'),
                    color: 'text-blue-600',
                    bg: 'bg-blue-50',
                    border: 'border-blue-200',
                    animate: 'animate-spin'
                }
            case 'failed':
                return {
                    icon: AlertCircle,
                    label: t('documents.status.failed'),
                    color: 'text-red-600',
                    bg: 'bg-red-50',
                    border: 'border-red-200'
                }
            default:
                return {
                    icon: Clock,
                    label: t('documents.status.pending'),
                    color: 'text-amber-600',
                    bg: 'bg-amber-50',
                    border: 'border-amber-200'
                }
        }
    }

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-black text-gray-900">{t('documents.title')}</h1>
                        <p className="text-gray-600 mt-1">{t('documents.subtitle')}</p>
                    </div>
                </div>

                {/* Upload Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative overflow-hidden bg-gradient-to-br from-primary-50 via-purple-50 to-pink-50 rounded-3xl p-8 border-2 border-dashed border-primary-200"
                >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-primary-200/30 rounded-full blur-3xl"></div>
                    <div className="relative z-10">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-white rounded-2xl shadow-lg">
                                <Upload className="w-6 h-6 text-primary-600" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">{t('documents.upload')}</h3>
                                <p className="text-sm text-gray-600">PDF, DOCX, TXT files supported</p>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-4">
                            <label className="flex-1 cursor-pointer">
                                <div className="flex items-center gap-3 px-6 py-4 bg-white border-2 border-gray-200 rounded-xl hover:border-primary-300 transition-all">
                                    <FileText className="w-5 h-5 text-gray-400" />
                                    <span className="text-sm text-gray-600 truncate">
                                        {selectedFile ? selectedFile.name : 'Choose a file...'}
                                    </span>
                                </div>
                                <input
                                    type="file"
                                    data-testid="document-file-input"
                                    onChange={handleFileSelect}
                                    accept=".pdf,.docx,.txt"
                                    className="hidden"
                                />
                            </label>
                            <button
                                onClick={handleUpload}
                                disabled={!selectedFile || uploadMutation.isLoading}
                                data-testid="document-upload-button"
                                className="px-8 py-4 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-xl hover:from-primary-700 hover:to-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold shadow-lg shadow-primary-200 flex items-center gap-2"
                            >
                                {uploadMutation.isLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        {t('documents.uploading')}
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-5 h-5" />
                                        {t('documents.uploadBtn')}
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </motion.div>

                {/* Documents Grid */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                    </div>
                ) : documents && documents.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <AnimatePresence>
                            {documents.map((doc: any, idx: number) => {
                                const statusConfig = getStatusConfig(doc.status)
                                const StatusIcon = statusConfig.icon

                                return (
                                    <motion.div
                                        key={doc.id}
                                        data-testid={`document-card-${doc.id}`}
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        transition={{ delay: idx * 0.05 }}
                                        className="group relative bg-white rounded-2xl border-2 border-gray-100 hover:border-primary-200 transition-all overflow-hidden shadow-sm hover:shadow-xl"
                                    >
                                        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary-100 to-purple-100 opacity-0 group-hover:opacity-100 blur-2xl transition-opacity"></div>

                                        <div className="relative p-6">
                                            <div className="flex items-start justify-between mb-4">
                                                <div className="p-3 bg-gradient-to-br from-primary-50 to-purple-50 rounded-xl">
                                                    <FileText className="w-6 h-6 text-primary-600" />
                                                </div>
                                                <button
                                                    onClick={() => deleteMutation.mutate(doc.id)}
                                                    disabled={deleteMutation.isLoading}
                                                    data-testid={`document-delete-${doc.id}`}
                                                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>

                                            <h3 className="font-bold text-gray-900 mb-2 truncate group-hover:text-primary-600 transition-colors">
                                                {doc.title}
                                            </h3>

                                            <div className="flex items-center gap-2 mb-4">
                                                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${statusConfig.bg} ${statusConfig.color} border ${statusConfig.border}`}>
                                                    <StatusIcon className={`w-3.5 h-3.5 ${statusConfig.animate || ''}`} />
                                                    {statusConfig.label}
                                                </span>
                                            </div>

                                            <div className="flex items-center justify-between text-sm">
                                                <span className="text-gray-500">
                                                    {doc.chunk_count} {t('documents.chunks')}
                                                </span>
                                                <span className="text-gray-400 text-xs">
                                                    {new Date(doc.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    </motion.div>
                                )
                            })}
                        </AnimatePresence>
                    </div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-center py-20"
                    >
                        <div className="inline-flex p-6 rounded-3xl bg-gradient-to-br from-gray-50 to-gray-100 mb-6">
                            <Sparkles className="w-12 h-12 text-gray-400" />
                        </div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-2">
                            {t('documents.noDocuments')}
                        </h3>
                        <p className="text-gray-600">
                            {t('documents.noDocumentsDesc')}
                        </p>
                    </motion.div>
                )}
            </div>
        </DashboardLayout>
    )
}
