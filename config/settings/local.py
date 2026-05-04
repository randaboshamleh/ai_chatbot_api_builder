from pathlib import Path
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BASE_URL = os.getenv('BASE_URL', 'http://localhost')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')

SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders',
    'apps.tenants',
    'apps.authentication',
    'apps.documents',
    'apps.chatbot',
    'apps.analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_USER_MODEL = 'tenants.TenantUser'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}

# Celery
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Ollama
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')
OLLAMA_EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')

# Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MAX_FILE_SIZE = 100 * 1024 * 1024

ALLOWED_DOCUMENT_TYPES = [
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

# Internationalization
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS - allow all for local development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# إعدادات التطوير المحلي
DEBUG = True
ALLOWED_HOSTS = ['*']

# Local-development helper: keep host-run Django connected to Docker infra.
def _local_env(key: str, default: str) -> str:
    return os.getenv(f'LOCAL_{key}', default)


# Database: PostgreSQL only (no SQLite fallback).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _local_env('DB_NAME', 'ai_db'),
        'USER': _local_env('DB_USER', 'ai_user'),
        'PASSWORD': _local_env('DB_PASSWORD', 'ai_pass'),
        'HOST': _local_env('DB_HOST', '127.0.0.1'),
        'PORT': _local_env('DB_PORT', '5433'),
    }
}

# LLM / vector store defaults for host-run Django talking to Docker services.
OLLAMA_BASE_URL = _local_env('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
CHROMA_HOST = _local_env('CHROMA_HOST', '127.0.0.1')
CHROMA_PORT = int(_local_env('CHROMA_PORT', '8001'))

# Celery Configuration
# Use local Redis port exposed from Docker.
LOCAL_REDIS_URL = _local_env('REDIS_URL', 'redis://:redis_pass@127.0.0.1:6380/0')
CELERY_BROKER_URL = LOCAL_REDIS_URL
CELERY_RESULT_BACKEND = LOCAL_REDIS_URL
# تعطيل eager mode لاستخدام Celery worker
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# CORS للتطوير
CORS_ALLOW_ALL_ORIGINS = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'assistify-local-cache',
    }
}

# Performance + reliability tuning
RAG_PIPELINE_CACHE_TTL_SECONDS = int(os.getenv('RAG_PIPELINE_CACHE_TTL_SECONDS', 600))
RAG_QUERY_CACHE_TTL_SECONDS = int(os.getenv('RAG_QUERY_CACHE_TTL_SECONDS', 90))
RAG_SUMMARY_CACHE_TTL_SECONDS = int(os.getenv('RAG_SUMMARY_CACHE_TTL_SECONDS', 300))
RAG_INDEXED_DOCS_CACHE_TTL_SECONDS = int(os.getenv('RAG_INDEXED_DOCS_CACHE_TTL_SECONDS', 30))
RAG_RETRIEVAL_K = int(os.getenv('RAG_RETRIEVAL_K', 4))
RAG_MIN_RELEVANCE_SCORE = float(os.getenv('RAG_MIN_RELEVANCE_SCORE', 0.50))
RAG_ENABLE_KEYWORD_SEARCH = os.getenv('RAG_ENABLE_KEYWORD_SEARCH', 'False').lower() == 'true'
RAG_KEYWORD_MIN_QUERY_LENGTH = int(os.getenv('RAG_KEYWORD_MIN_QUERY_LENGTH', 4))
RAG_ANSWER_MAX_TOKENS = int(os.getenv('RAG_ANSWER_MAX_TOKENS', 140))
RAG_SUMMARY_MAX_TOKENS = int(os.getenv('RAG_SUMMARY_MAX_TOKENS', 150))
RAG_MAX_CONTEXT_CHARS = int(os.getenv('RAG_MAX_CONTEXT_CHARS', 2500))
RAG_MAX_RESPONSE_SECONDS = float(os.getenv('RAG_MAX_RESPONSE_SECONDS', 90))
RAG_MAX_SUMMARY_SECONDS = float(os.getenv('RAG_MAX_SUMMARY_SECONDS', 45))
RAG_SINGLE_DOCUMENT_BIAS = os.getenv('RAG_SINGLE_DOCUMENT_BIAS', 'True').lower() == 'true'
RAG_DOCUMENT_CONFIDENCE_MARGIN = float(os.getenv('RAG_DOCUMENT_CONFIDENCE_MARGIN', 0.06))
RAG_MIN_ARABIC_ANSWER_RATIO = float(os.getenv('RAG_MIN_ARABIC_ANSWER_RATIO', 0.60))
RAG_ENABLE_ARABIC_REWRITE = os.getenv('RAG_ENABLE_ARABIC_REWRITE', 'False').lower() == 'true'
RAG_REWRITE_MAX_TOKENS = int(os.getenv('RAG_REWRITE_MAX_TOKENS', 96))
RAG_REWRITE_TIMEOUT_SECONDS = float(os.getenv('RAG_REWRITE_TIMEOUT_SECONDS', 20))
RAG_MAX_PRIMARY_SECONDS_BEFORE_SKIP_REWRITE = float(
    os.getenv('RAG_MAX_PRIMARY_SECONDS_BEFORE_SKIP_REWRITE', 25)
)
RAG_ENABLE_FALLBACK_ARABIC_REWRITE = os.getenv('RAG_ENABLE_FALLBACK_ARABIC_REWRITE', 'True').lower() == 'true'
RAG_FALLBACK_REWRITE_MAX_TOKENS = int(os.getenv('RAG_FALLBACK_REWRITE_MAX_TOKENS', 90))
RAG_FALLBACK_REWRITE_TIMEOUT_SECONDS = float(os.getenv('RAG_FALLBACK_REWRITE_TIMEOUT_SECONDS', 12))
OLLAMA_REQUEST_TIMEOUT_SECONDS = float(os.getenv('OLLAMA_REQUEST_TIMEOUT_SECONDS', 120))

CHANNEL_SESSION_CACHE_TTL_SECONDS = int(os.getenv('CHANNEL_SESSION_CACHE_TTL_SECONDS', 604800))
TELEGRAM_PROCESSING_MODE = os.getenv('TELEGRAM_PROCESSING_MODE', 'celery')
WHATSAPP_PROCESSING_MODE = os.getenv('WHATSAPP_PROCESSING_MODE', 'celery')
