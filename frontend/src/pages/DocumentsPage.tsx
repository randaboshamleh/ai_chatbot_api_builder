import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useTranslation } from 'react-i18next'
import { Upload, FileText, Trash2, CheckCircle, Clock, AlertCircle, Loader2, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import DashboardLayout from '../components/Layout/DashboardLayout'
import { Document, documentService } from '../services/documentService'

type UploadNotice = {
    id: string
    title: string
    estimatedWaitSeconds: number
}

export default function DocumentsPage() {
    const { t, i18n } = useTranslation()
    const isArabic = i18n.language === 'ar'

    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [uploadNotice, setUploadNotice] = useState<UploadNotice | null>(null)
    const queryClient = useQueryClient()

    const { data: documents = [], isLoading, isFetching } = useQuery<Document[]>(
        'documents',
        documentService.list,
        {
            refetchInterval: (data) => {
                const list = data || []
                const hasActiveWork = list.some((doc) => doc.status === 'pending' || doc.status === 'processing')
                return hasActiveWork ? 5000 : false
            },
            refetchOnWindowFocus: true,
        }
    )

    const uploadMutation = useMutation(documentService.upload, {
        onSuccess: (uploadedDoc: any) => {
            const estimatedWaitSeconds =
                uploadedDoc?.estimated_wait_seconds ||
                documentService.estimateWaitSeconds(selectedFile?.size || uploadedDoc?.file_size || 0)

            setUploadNotice({
                id: uploadedDoc.id,
                title: uploadedDoc.title || selectedFile?.name || 'Document',
                estimatedWaitSeconds,
            })

            queryClient.invalidateQueries('documents')
            setSelectedFile(null)

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
            if (fileInput) fileInput.value = ''
        },
        onError: (error: any) => {
            console.error('Upload error:', error)
            alert(t('documents.uploadError') + ': ' + (error.response?.data?.error || error.message))
        },
    })

    const deleteMutation = useMutation(documentService.delete, {
        onSuccess: () => {
            queryClient.invalidateQueries('documents')
        },
    })

    const processingDocuments = useMemo(
        () => documents.filter((doc) => doc.status === 'pending' || doc.status === 'processing'),
        [documents]
    )

    useEffect(() => {
        if (!uploadNotice) return
        const doc = documents.find((item) => item.id === uploadNotice.id)
        if (!doc) return
        if (doc.status === 'indexed' || doc.status === 'failed') {
            setUploadNotice(null)
        }
    }, [documents, uploadNotice])

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
                    border: 'border-emerald-200',
                }
            case 'processing':
                return {
                    icon: Loader2,
                    label: t('documents.status.processing'),
                    color: 'text-blue-600',
                    bg: 'bg-blue-50',
                    border: 'border-blue-200',
                    animate: 'animate-spin',
                }
            case 'failed':
                return {
                    icon: AlertCircle,
                    label: t('documents.status.failed'),
                    color: 'text-red-600',
                    bg: 'bg-red-50',
                    border: 'border-red-200',
                }
            default:
                return {
                    icon: Clock,
                    label: t('documents.status.pending'),
                    color: 'text-amber-600',
                    bg: 'bg-amber-50',
                    border: 'border-amber-200',
                }
        }
    }

    const formatProcessingHint = (doc: Document) => {
        const estimated = doc.estimated_wait_seconds || documentService.estimateWaitSeconds(doc.file_size)
        const estimatedMinutes = Math.max(1, Math.ceil(estimated / 60))
        const elapsedMinutes = Math.max(0, Math.floor((Date.now() - new Date(doc.created_at).getTime()) / 60000))

        if (isArabic) {
            return `قيد الفهرسة... مر ${elapsedMinutes} د، والمدة المتوقعة ${estimatedMinutes} د`;
        }
        return `Indexing... ${elapsedMinutes}m elapsed, ~${estimatedMinutes}m expected`
    }

    const globalWaitMinutes = useMemo(() => {
        const fromDocs = processingDocuments.map((doc) =>
            Math.ceil((doc.estimated_wait_seconds || documentService.estimateWaitSeconds(doc.file_size)) / 60)
        )
        if (uploadNotice) {
            fromDocs.push(Math.ceil(uploadNotice.estimatedWaitSeconds / 60))
        }
        return Math.max(1, ...(fromDocs.length ? fromDocs : [1]))
    }, [processingDocuments, uploadNotice])

    const showWaitingBanner = uploadMutation.isLoading || processingDocuments.length > 0 || !!uploadNotice

    return (
        <DashboardLayout>
            <div className="space-y-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-black text-gray-900">{t('documents.title')}</h1>
                        <p className="text-gray-600 mt-1">{t('documents.subtitle')}</p>
                    </div>
                    {isFetching && processingDocuments.length > 0 && (
                        <span className="text-xs text-blue-700 bg-blue-50 border border-blue-200 px-3 py-1 rounded-full">
                            {isArabic ? 'تحديث الحالة كل 5 ثوانٍ' : 'Refreshing every 5s'}
                        </span>
                    )}
                </div>

                {showWaitingBanner && (
                    <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl"
                    >
                        <Loader2 className="w-5 h-5 text-amber-600 animate-spin mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-sm font-semibold text-amber-900">
                                {isArabic
                                    ? `جاري تجهيز الوثيقة للبحث الذكي. قد تستغرق العملية حوالي ${globalWaitMinutes} دقيقة.`
                                    : `Your document is being indexed. It may take around ${globalWaitMinutes} minute(s).`}
                            </p>
                            <p className="text-xs text-amber-800">
                                {isArabic
                                    ? 'يمكنك المتابعة في النظام الآن، وسيتم تحديث الحالة تلقائيًا حتى تصبح الوثيقة مفهرسة.'
                                    : 'You can continue using the app. Document status will update automatically once indexing is done.'}
                            </p>
                        </div>
                    </motion.div>
                )}

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
                            <label className="flex-1 cursor-pointer group">
                                <div
                                    className={`flex items-center gap-3 px-6 py-4 bg-white border-2 rounded-xl transition-all ${
                                        selectedFile ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:border-primary-300'
                                    }`}
                                >
                                    <FileText className={`w-5 h-5 ${selectedFile ? 'text-primary-600' : 'text-gray-400'}`} />
                                    <span
                                        className={`text-sm font-medium truncate ${
                                            selectedFile ? 'text-primary-900' : 'text-gray-500'
                                        }`}
                                    >
                                        {selectedFile ? selectedFile.name : t('documents.chooseFile')}
                                    </span>
                                    {selectedFile && (
                                        <span className="ml-auto text-xs text-primary-600 font-semibold">
                                            {(selectedFile.size / 1024).toFixed(1)} KB
                                        </span>
                                    )}
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
                                className="px-8 py-4 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-xl hover:from-primary-700 hover:to-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold shadow-lg shadow-primary-200 flex items-center justify-center gap-2 whitespace-nowrap"
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

                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                    </div>
                ) : documents && documents.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <AnimatePresence>
                            {documents.map((doc: Document, idx: number) => {
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

                                            <h3
                                                className="font-bold text-gray-900 mb-2 truncate group-hover:text-primary-600 transition-colors"
                                                title={doc.title}
                                            >
                                                {doc.title}
                                            </h3>

                                            <div className="flex flex-wrap items-center gap-2 mb-3">
                                                <span
                                                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${statusConfig.bg} ${statusConfig.color} border ${statusConfig.border}`}
                                                >
                                                    <StatusIcon className={`w-3.5 h-3.5 ${statusConfig.animate || ''}`} />
                                                    {statusConfig.label}
                                                </span>
                                            </div>

                                            {(doc.status === 'pending' || doc.status === 'processing') && (
                                                <p className="text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-2 py-1 mb-3">
                                                    {formatProcessingHint(doc)}
                                                </p>
                                            )}

                                            {doc.status === 'failed' && doc.error_message && (
                                                <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-2 py-1 mb-3 line-clamp-2">
                                                    {doc.error_message}
                                                </p>
                                            )}

                                            <div className="flex items-center justify-between text-sm">
                                                <span className="text-gray-500">
                                                    {doc.chunk_count} {t('documents.chunks')}
                                                </span>
                                                <span className="text-gray-400 text-xs font-medium">
                                                    {new Date(doc.created_at).toLocaleDateString('en-GB', {
                                                        day: '2-digit',
                                                        month: '2-digit',
                                                        year: 'numeric',
                                                    })}
                                                </span>
                                            </div>
                                        </div>
                                    </motion.div>
                                )
                            })}
                        </AnimatePresence>
                    </div>
                ) : (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-20">
                        <div className="inline-flex p-6 rounded-3xl bg-gradient-to-br from-gray-50 to-gray-100 mb-6">
                            <Sparkles className="w-12 h-12 text-gray-400" />
                        </div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-2">{t('documents.noDocuments')}</h3>
                        <p className="text-gray-600">{t('documents.noDocumentsDesc')}</p>
                    </motion.div>
                )}
            </div>
        </DashboardLayout>
    )
}