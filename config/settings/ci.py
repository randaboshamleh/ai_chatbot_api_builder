"""
CI-specific Django settings.
Uses SQLite, no external services (Ollama, ChromaDB, Redis).
"""
from pathlib import Path
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'ci-test-secret-key-not-for-production')
DEBUG = True
ALLOWED_HOSTS = ['*']

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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
}

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
CORS_ALLOW_ALL_ORIGINS = True

MAX_FILE_SIZE = 100 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

OLLAMA_MODEL = 'llama3'
OLLAMA_EMBEDDING_MODEL = 'nomic-embed-text'
OLLAMA_BASE_URL = 'http://localhost:11434'
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000

# Run Celery tasks synchronously in CI (no worker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'assistify-ci-cache',
    }
}

RAG_PIPELINE_CACHE_TTL_SECONDS = 120
RAG_QUERY_CACHE_TTL_SECONDS = 30
RAG_SUMMARY_CACHE_TTL_SECONDS = 60
RAG_INDEXED_DOCS_CACHE_TTL_SECONDS = 10
RAG_RETRIEVAL_K = 4
RAG_MIN_RELEVANCE_SCORE = 0.50
RAG_ENABLE_KEYWORD_SEARCH = False
RAG_KEYWORD_MIN_QUERY_LENGTH = 4
RAG_ANSWER_MAX_TOKENS = 220
RAG_SUMMARY_MAX_TOKENS = 120
RAG_MAX_CONTEXT_CHARS = 2500

CHANNEL_SESSION_CACHE_TTL_SECONDS = 3600
TELEGRAM_PROCESSING_MODE = 'sync'
WHATSAPP_PROCESSING_MODE = 'sync'
