# AI Chatbot API Builder - Assistify

نظام شات بوت ذكي متعدد المستأجرين مع RAG (Retrieval-Augmented Generation) باستخدام Django و Ollama.

[![CI/CD Pipeline](https://github.com/randaboshamleh/ai_chatbot_api_builder/actions/workflows/ci.yml/badge.svg)](https://github.com/randaboshamleh/ai_chatbot_api_builder/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-75%2B%20passing-brightgreen)](./TESTING.md)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green)](./htmlcov/index.html)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

## 🧪 Testing & Quality Assurance

This project includes comprehensive testing following industry best practices:

- **✅ Unit Tests**: 30+ tests covering core business logic (85% coverage)
- **✅ Integration Tests**: 15+ tests for API endpoints and database operations
- **✅ Performance Tests**: Load testing with Locust (up to 100 concurrent users)
- **✅ E2E Tests**: 34 Playwright tests for complete user journeys (NEW!)
- **✅ CI/CD Pipeline**: Automated testing with GitHub Actions
- **✅ Security**: GitLeaks scanning for secrets
- **✅ Performance Results**: Latest measured results documented in `tests/performance/ACTUAL_TEST_RESULTS.md`

### Quick Test Commands

```bash
# Run all Python tests
pytest apps/tests/ -v --cov=apps --cov=core

# Run unit tests only
pytest apps/tests/test_unit.py -v

# Run integration tests
DJANGO_SETTINGS_MODULE=ci_settings pytest apps/tests/test_integration.py -v

# Run performance tests (requires running server)
cd tests/performance && locust -f locustfile.py --headless -u 50 -r 10 -t 1m

# Run E2E tests (NEW!)
cd frontend
npm run test:e2e          # Run all E2E tests
npm run test:e2e:ui       # Interactive UI mode
npm run test:e2e:headed   # See browser in action

# CI smoke E2E (same profile used in pipeline)
npm run test:e2e -- --grep @smoke
```

📚 **Full Testing Documentation**: See [TESTING.md](./TESTING.md) for detailed information.  
🎭 **E2E Testing Guide**: See [E2E_TESTING_GUIDE.md](./E2E_TESTING_GUIDE.md) for Playwright setup.  
⚡ **Quick Start E2E**: See [QUICK_START_E2E.md](./QUICK_START_E2E.md) for fast setup.  
🚀 **Quick Commands**: See [TEST_COMMANDS.txt](./TEST_COMMANDS.txt) for copy-paste commands.

---

## ⚠️ ملاحظة مهمة حول Python 3.14

**ChromaDB غير متوافق حالياً مع Python 3.14**. لذلك تم تعطيل وظائف Vector Store مؤقتاً.

### 🚀 الحل السريع (موصى به)

**استخدم Python 3.11 للحصول على RAG كامل:**

```powershell
# تشغيل script الإعداد التلقائي
.\setup_python311.ps1
```

أو اتبع التعليمات المفصلة في ملف: [`SETUP_PYTHON311.md`](SETUP_PYTHON311.md)

### الحلول المتاحة:
1. ✅ **استخدام Python 3.11 أو 3.12** (الأفضل - RAG كامل)
2. ⚠️ **الاستمرار مع Python 3.14** (النظام يعمل بدون ChromaDB)
3. ⏳ **انتظار تحديث ChromaDB** لدعم Python 3.14

## ✅ المشاكل التي تم إصلاحها

### 1. مشاكل الإعدادات
- ✅ إصلاح خطأ في `SSIMPLE_JWT` → `SIMPLE_JWT`
- ✅ إصلاح تكرار إعدادات CORS
- ✅ إصلاح تكرار إعدادات Celery
- ✅ إصلاح إعدادات Ollama embedding model
- ✅ فصل إعدادات التطوير والإنتاج

### 2. مشاكل المكتبات
- ✅ تحديث PyTorch إلى إصدار متوافق (`torch>=2.0.0`)
- ✅ إصلاح مشكلة `unstructured` version compatibility
- ✅ إصلاح استيراد `langchain.text_splitter` → `langchain_text_splitters`
- ✅ إضافة معالجة أخطاء للمكتبات المفقودة
- ⚠️ تعطيل ChromaDB مؤقتاً بسبب عدم التوافق مع Python 3.14

### 3. مشاكل RAG Pipeline
- ✅ إضافة دعم streaming للإجابات
- ✅ إصلاح معالجة الأخطاء في streaming
- ✅ تحسين cache management
- ✅ إضافة fallback عند عدم توفر ChromaDB
- ✅ دعم Ollama للـ LLM (بدون vector search)

### 4. مشاكل Vector Store
- ✅ إصلاح indentation في delete_document method
- ✅ تحسين error handling
- ✅ إضافة معالجة للحالات عند عدم توفر ChromaDB

### 5. مشاكل البنية
- ✅ إنشاء إعدادات منفصلة للتطوير والإنتاج
- ✅ إصلاح مسارات الاستيراد
- ✅ إضافة معالجة شاملة للأخطاء

## 🚀 التشغيل السريع

### المتطلبات الأساسية
```bash
# تثبيت المكتبات الأساسية
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers
pip install celery redis langchain-text-splitters pypdf python-docx ollama
```

### إعداد قاعدة البيانات
```bash
python manage.py migrate
python manage.py createsuperuser
```

### تشغيل الخادم
```bash
python manage.py runserver
```

## 🤖 تفعيل Ollama للـ LLM

### 1. تثبيت Ollama
```bash
# Windows/Mac/Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. تحميل النماذج
```bash
ollama pull llama3
ollama pull nomic-embed-text
```

### 3. تشغيل Ollama
```bash
ollama serve
```

## 📋 اختبار النظام

### 1. الوصول للوحة الإدارة
```
http://localhost:8000/admin/
```

### 2. إنشاء مستأجر جديد
```bash
curl -X POST http://localhost:8000/api/v1/tenants/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Company", "slug": "test-company"}'
```

### 3. إرسال استعلام للشات بوت
```bash
export API_KEY="replace-with-your-api-key"

curl -X POST http://localhost:8000/api/v1/chat/query/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"question": "مرحبا، كيف يمكنني مساعدتك؟"}'
```

## 🔍 الأسباب وراء المشاكل الأصلية

### 1. عدم تثبيت المكتبات
**السبب**: لم يتم تشغيل `pip install -r requirements.txt`
**الحل**: تثبيت جميع المكتبات المطلوبة بالإصدارات الصحيحة

### 2. إعدادات خاطئة
**السبب**: أخطاء إملائية وتكرار في ملف settings.py
**الحل**: مراجعة وتصحيح جميع الإعدادات مع فصل بيئات التطوير والإنتاج

### 3. عدم توافق الإصدارات
**السبب**: استخدام إصدارات غير متوافقة مع Python 3.14
**الحل**: تحديث المكتبات وإضافة معالجة للأخطاء

### 4. مشاكل في streaming
**السبب**: عدم معالجة streaming بشكل صحيح في RAG pipeline
**الحل**: إضافة دعم streaming مع معالجة صحيحة للأخطاء

### 5. عدم توفر الخدمات الخارجية
**السبب**: الاعتماد على Ollama و ChromaDB دون معالجة حالة عدم توفرهما
**الحل**: إضافة fallback mechanisms وmessages واضحة للمستخدم

## 🎯 الحالة الحالية

النظام الآن يعمل بشكل صحيح مع:
- ✅ Django server يعمل بدون أخطاء
- ✅ قاعدة البيانات تم إنشاؤها وتهيئتها
- ✅ جميع التطبيقات تعمل بشكل صحيح
- ✅ API endpoints متاحة
- ✅ معالجة شاملة للأخطاء
- ✅ دعم Ollama للـ LLM
- ⚠️ ChromaDB معطل مؤقتاً (عدم توافق مع Python 3.14)

## 🔧 الميزات المتاحة حالياً

- 🏢 **Multi-tenant**: عزل تام للبيانات بين الشركات
- 🤖 **LLM Integration**: توليد الإجابات باستخدام Ollama
- 📄 **Document Processing**: دعم PDF, Word, Text (بدون vector search)
- 🔊 **Voice Support**: استعلامات صوتية باستخدام Whisper
- 🔄 **Streaming**: إجابات متدفقة في الوقت الفعلي
- 🔐 **Security**: تشفير وحماية البيانات
- 📊 **Analytics**: تتبع الاستخدام والإحصائيات
- 🛡️ **Error Handling**: معالجة شاملة للأخطاء والحالات الاستثنائية

## 🐳 التشغيل باستخدام Docker

### البدء السريع
```powershell
# إعادة بناء واختبار Docker
.\rebuild_docker.ps1
```

### أو يدوياً
```powershell
# إيقاف وحذف الحاويات القديمة
docker-compose down --rmi all

# إعادة البناء
docker-compose build --no-cache

# التشغيل
docker-compose up -d

# تشغيل الترحيلات
docker-compose exec api python manage.py migrate

# تنزيل نماذج Ollama
docker-compose exec ollama ollama pull llama3.2:1b
docker-compose exec ollama ollama pull nomic-embed-text
```

### اختبار API في Docker
```powershell
# اختبار endpoint
$env:API_KEY = "replace-with-your-api-key"
.\test_api.ps1 -ApiKey $env:API_KEY -Question "ما هي الخدمات؟"
```

### حل مشاكل Docker
راجع الدليل الشامل: [`DOCKER_TROUBLESHOOTING.md`](DOCKER_TROUBLESHOOTING.md)

**المشاكل الشائعة:**
- ✅ 502 Bad Gateway → تم إصلاح ChromaDB version mismatch
- ✅ Worker Timeout → تم زيادة timeout إلى 300 ثانية
- ✅ NumPy compatibility → تم تثبيت numpy<2.0

## 🏗️ البنية التقنية

- **Backend**: Django + DRF
- **Database**: SQLite (تطوير) / PostgreSQL (إنتاج)
- **LLM**: Ollama (متاح)
- **Vector DB**: ChromaDB 0.4.22 (متوافق مع Python 3.11)
- **Queue**: Celery + Redis (للإنتاج)
- **Deployment**: Docker + Docker Compose

## 📝 ملاحظات مهمة

1. **النظام يعمل بدون ChromaDB**: سيعرض رسائل واضحة عند عدم توفر vector search
2. **Ollama متاح**: يمكن استخدام LLM للإجابة على الأسئلة العامة
3. **للحصول على RAG كامل**: استخدم Python 3.11 أو 3.12
4. **للتطوير**: استخدم SQLite وCelery eager mode
5. **للإنتاج**: استخدم PostgreSQL وRedis وDocker
6. **الأمان**: غيّر SECRET_KEY في الإنتاج

## 🔄 كيفية تفعيل RAG الكامل

### الخيار 1: استخدام Python 3.11/3.12
```bash
# إنشاء بيئة افتراضية جديدة مع Python 3.11
pyenv install 3.11.9
pyenv virtualenv 3.11.9 chatbot-env
pyenv activate chatbot-env

# تثبيت المكتبات مع ChromaDB
pip install -r requirements.txt
pip install chromadb==0.4.22
```

### الخيار 2: انتظار تحديث ChromaDB
راقب تحديثات ChromaDB لدعم Python 3.14 في المستقبل.

## 🎉 الخلاصة

النظام الآن **يعمل بشكل كامل** مع جميع الوظائف الأساسية. الوحيد المفقود هو vector search بسبب عدم توافق ChromaDB مع Python 3.14. يمكنك:

1. **استخدام النظام الآن** للشات بوت العادي مع Ollama
2. **رفع الوثائق** (ستُحفظ في قاعدة البيانات)
3. **إدارة المستأجرين** والمستخدمين
4. **تفعيل RAG لاحقاً** عند توفر ChromaDB متوافق

---

## 📚 Additional Documentation

- **[TESTING.md](./TESTING.md)** - Comprehensive testing documentation
- **[SETUP_PYTHON311.md](./SETUP_PYTHON311.md)** - Python 3.11 setup guide
- **[DOCKER_TROUBLESHOOTING.md](./DOCKER_TROUBLESHOOTING.md)** - Docker troubleshooting guide

---

## 👥 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🎓 Academic Project

This project was developed as part of the Software Testing course at Syrian Private University (SPU).

**Course**: Software Testing - Practical  
**Instructor**: Eng. Mohamed Al Balkhi  
**Year**: 2026

## 👥 Team Members

- `randaboshamleh` (individual submission)

## 🔗 Repository

- https://github.com/randaboshamleh/ai_chatbot_api_builder

---

**Last Updated**: 2026-04-20
