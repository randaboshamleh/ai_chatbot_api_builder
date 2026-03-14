import { useTranslation } from 'react-i18next'
import { Languages } from 'lucide-react'

export default function LanguageSwitcher() {
    const { i18n } = useTranslation()

    const toggleLanguage = () => {
        const newLang = i18n.language === 'en' ? 'ar' : 'en'
        i18n.changeLanguage(newLang)
        localStorage.setItem('language', newLang)
        document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr'
        document.documentElement.lang = newLang
    }

    return (
        <button
            onClick={toggleLanguage}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title={i18n.language === 'en' ? 'Switch to Arabic' : 'التبديل للإنجليزية'}
        >
            <Languages className="w-4 h-4" />
            <span>{i18n.language === 'en' ? 'العربية' : 'English'}</span>
        </button>
    )
}
