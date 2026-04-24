from pathlib import Path
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')
BASE_URL = os.getenv('BASE_URL', 'http://localhost')

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
AUTH_USER_MODEL = 'tenants.TenantUser'
WSGI_APPLICATION = 'config.wsgi.application'

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'ai_db'),
        'USER': os.getenv('DB_USER', 'ai_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'ai_pass'),
        'HOST': os.getenv('DB_HOST', 'postgres'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

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
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

MAX_FILE_SIZE = 100 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')
OLLAMA_EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', 8000))

CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://:redis_pass@redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://:redis_pass@redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'assistify-production-cache',
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
RAG_ANSWER_MAX_TOKENS = int(os.getenv('RAG_ANSWER_MAX_TOKENS', 260))
RAG_SUMMARY_MAX_TOKENS = int(os.getenv('RAG_SUMMARY_MAX_TOKENS', 150))
RAG_MAX_CONTEXT_CHARS = int(os.getenv('RAG_MAX_CONTEXT_CHARS', 2500))
RAG_MAX_RESPONSE_SECONDS = float(os.getenv('RAG_MAX_RESPONSE_SECONDS', 75))
RAG_MAX_SUMMARY_SECONDS = float(os.getenv('RAG_MAX_SUMMARY_SECONDS', 45))
RAG_SINGLE_DOCUMENT_BIAS = os.getenv('RAG_SINGLE_DOCUMENT_BIAS', 'True').lower() == 'true'
RAG_DOCUMENT_CONFIDENCE_MARGIN = float(os.getenv('RAG_DOCUMENT_CONFIDENCE_MARGIN', 0.06))
RAG_MIN_ARABIC_ANSWER_RATIO = float(os.getenv('RAG_MIN_ARABIC_ANSWER_RATIO', 0.72))

CHANNEL_SESSION_CACHE_TTL_SECONDS = int(os.getenv('CHANNEL_SESSION_CACHE_TTL_SECONDS', 604800))
TELEGRAM_PROCESSING_MODE = os.getenv('TELEGRAM_PROCESSING_MODE', 'celery')
WHATSAPP_PROCESSING_MODE = os.getenv('WHATSAPP_PROCESSING_MODE', 'celery')
