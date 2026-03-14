# AI Chatbot Frontend

واجهة المستخدم لمنصة الشات بوت الذكي المبنية على React + TypeScript + Vite.

## المتطلبات

- Node.js 18+ و npm أو yarn

## التثبيت

```bash
cd frontend
npm install
```

## التشغيل في بيئة التطوير

```bash
npm run dev
```

سيعمل التطبيق على `http://localhost:5173`

## البناء للإنتاج

```bash
npm run build
```

## المميزات

- ✅ React 18 مع TypeScript
- ✅ Vite للبناء السريع
- ✅ TailwindCSS للتصميم
- ✅ React Router للتنقل
- ✅ Zustand لإدارة الحالة
- ✅ React Query لإدارة البيانات
- ✅ Axios للطلبات
- ✅ دعم RTL للعربية
- ✅ تصميم متجاوب

## الصفحات

- `/` - الصفحة الرئيسية
- `/login` - تسجيل الدخول
- `/register` - إنشاء حساب
- `/dashboard` - لوحة التحكم
- `/documents` - إدارة الوثائق
- `/chat` - المحادثة مع الشات بوت
- `/analytics` - التحليلات والإحصائيات
- `/settings` - الإعدادات
- `/channels` - ربط القنوات (تيليجرام/واتساب)

## البنية

```
frontend/
├── src/
│   ├── components/     # المكونات القابلة لإعادة الاستخدام
│   ├── pages/          # صفحات التطبيق
│   ├── services/       # خدمات API
│   ├── stores/         # إدارة الحالة
│   ├── utils/          # دوال مساعدة
│   ├── App.tsx         # المكون الرئيسي
│   └── main.tsx        # نقطة الدخول
├── public/             # الملفات الثابتة
└── index.html          # HTML الرئيسي
```

## الاتصال بالـ Backend

تأكد من تشغيل الـ Backend على `http://localhost:8000` أو قم بتعديل `VITE_API_URL` في ملف `.env`:

```env
VITE_API_URL=http://localhost:8000/api
```
