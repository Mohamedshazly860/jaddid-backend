# Jaddid Marketplace App - Complete Documentation
# توثيق تطبيق سوق جديد - التوثيق الكامل

---

## English Documentation

### Overview
The **Jaddid Marketplace** app is a comprehensive Django REST Framework application designed for buying and selling recyclable materials. It provides a complete marketplace solution with product listings, orders, reviews, messaging, and reporting features.

### Features Implemented

#### 1. **Models** (8 Core Models)

##### Category Model
- Hierarchical category structure for organizing recyclable materials
- Support for parent-child relationships
- Bilingual support (English & Arabic)
- Icon/image support for categories

##### Product Model
- Complete product listing with bilingual support
- Multiple condition options (New, Like New, Good, Fair, Poor)
- Status management (Draft, Active, Sold, Reserved, Deleted)
- Pricing and quantity management
- Location with GPS coordinates (latitude/longitude)
- View and favorite counters
- Automatic publish date tracking

##### ProductImage Model
- Multiple images per product
- Primary image designation
- Image ordering support
- Automatic organization by date

##### Favorite Model
- User wishlist/favorites functionality
- Unique constraint per user-product combination
- Fast lookups with database indexes

##### Order Model
- Complete order management system
- Auto-generated unique order numbers
- Order status tracking (Pending, Confirmed, In Progress, Completed, Cancelled, Refunded)
- Payment status tracking (Unpaid, Paid, Partial)
- Automatic total price calculation
- Delivery address support

##### Review Model
- 5-star rating system
- Verified purchase indicator
- Admin approval system
- Title and comment fields
- Linked to orders for purchase verification

##### Message Model
- Direct messaging between buyers and sellers
- Product-specific conversations
- Read/unread status tracking
- Subject and message body

##### Report Model
- Content moderation system
- Multiple report reasons (Spam, Inappropriate, Fraud, Duplicate, Other)
- Status tracking (Pending, Reviewing, Resolved, Dismissed)
- Admin notes and resolution tracking

#### 2. **Serializers** (10 Serializers)
- **CategorySerializer**: Full category data with subcategories
- **ProductListSerializer**: Lightweight for list views
- **ProductDetailSerializer**: Complete product information
- **ProductCreateUpdateSerializer**: Product creation/editing with image upload
- **ProductImageSerializer**: Image management
- **FavoriteSerializer**: Wishlist management
- **OrderSerializer**: Order processing
- **ReviewSerializer**: Review submission
- **MessageSerializer**: Messaging functionality
- **ReportSerializer**: Content reporting

#### 3. **ViewSets & API Endpoints** (7 ViewSets)

##### CategoryViewSet
- `GET /api/marketplace/categories/` - List all categories
- `GET /api/marketplace/categories/{id}/` - Category details
- `GET /api/marketplace/categories/tree/` - Category tree structure
- `GET /api/marketplace/categories/{id}/products/` - Products in category
- `POST /api/marketplace/categories/` - Create category (admin)
- `PUT/PATCH /api/marketplace/categories/{id}/` - Update category (admin)
- `DELETE /api/marketplace/categories/{id}/` - Delete category (admin)

##### ProductViewSet
- `GET /api/marketplace/products/` - List all active products
- `GET /api/marketplace/products/{id}/` - Product details (increments view count)
- `GET /api/marketplace/products/my_products/` - User's own products
- `POST /api/marketplace/products/` - Create product
- `PUT/PATCH /api/marketplace/products/{id}/` - Update product (owner only)
- `DELETE /api/marketplace/products/{id}/` - Delete product (owner only)
- `POST /api/marketplace/products/{id}/toggle_favorite/` - Add/remove favorite
- `GET /api/marketplace/products/{id}/reviews/` - Product reviews
- `POST /api/marketplace/products/{id}/publish/` - Publish draft product

**Filtering & Search:**
- Filter by: category, condition, status, seller, price range
- Search in: title, description, location
- Order by: price, created_at, views_count, favorites_count

##### FavoriteViewSet
- `GET /api/marketplace/favorites/` - User's favorites
- `POST /api/marketplace/favorites/` - Add to favorites
- `DELETE /api/marketplace/favorites/{id}/` - Remove from favorites

##### OrderViewSet
- `GET /api/marketplace/orders/` - User's orders (as buyer or seller)
- `GET /api/marketplace/orders/purchases/` - Orders as buyer
- `GET /api/marketplace/orders/sales/` - Orders as seller
- `POST /api/marketplace/orders/` - Create order
- `POST /api/marketplace/orders/{id}/confirm/` - Confirm order (seller)
- `POST /api/marketplace/orders/{id}/complete/` - Complete order (seller)
- `POST /api/marketplace/orders/{id}/cancel/` - Cancel order (buyer/seller)

##### ReviewViewSet
- `GET /api/marketplace/reviews/` - List all reviews
- `GET /api/marketplace/reviews/my_reviews/` - User's reviews
- `POST /api/marketplace/reviews/` - Create review
- `PUT/PATCH /api/marketplace/reviews/{id}/` - Update review (owner)
- `DELETE /api/marketplace/reviews/{id}/` - Delete review (owner)

##### MessageViewSet
- `GET /api/marketplace/messages/` - All messages
- `GET /api/marketplace/messages/inbox/` - Received messages
- `GET /api/marketplace/messages/sent/` - Sent messages
- `GET /api/marketplace/messages/unread_count/` - Unread message count
- `POST /api/marketplace/messages/` - Send message
- `POST /api/marketplace/messages/{id}/mark_read/` - Mark as read

##### ReportViewSet
- `GET /api/marketplace/reports/` - User's reports (all for admin)
- `GET /api/marketplace/reports/my_reports/` - User's own reports
- `POST /api/marketplace/reports/` - Create report
- `PUT/PATCH /api/marketplace/reports/{id}/` - Update report (admin)

#### 4. **Permissions**
- **IsSellerOrReadOnly**: Only product sellers can edit their products
- **IsOwnerOrReadOnly**: Only resource owners can edit
- **IsAdminOrReadOnly**: Only admins can edit certain resources
- **IsAuthenticatedOrReadOnly**: Public read access, authenticated write

#### 5. **Admin Panel**
Comprehensive admin interfaces for all models with:
- Custom list displays with relevant fields
- Filtering and search capabilities
- Inline editing (e.g., product images)
- Custom actions (bulk operations)
- Read-only fields for system-generated data
- Organized fieldsets for better UX

#### 6. **Database Features**
- **Indexes**: Strategic indexes for performance
  - Seller products lookup
  - Category products
  - Order tracking by status
  - Message inbox queries
  - Search optimization
- **Unique Constraints**: Data integrity (favorites, reviews)
- **Foreign Keys**: Proper relationships with CASCADE/PROTECT
- **UUID Primary Keys**: Security and scalability

### Security Features

1. **Environment Variables**: Sensitive data in .env file
2. **Database Password Protection**: Password not hardcoded
3. **Permission Classes**: Role-based access control
4. **Input Validation**: Serializer validation
5. **CORS Configuration**: Frontend origin restrictions
6. **JWT Authentication**: Token-based auth ready

### Database Configuration

#### Team Collaboration Setup
The project uses PostgreSQL with the following secure configuration:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

**For Team Members:**
1. Copy `.env.example` to `.env`
2. Update database credentials to match your local setup
3. Never commit `.env` file to Git
4. Each team member uses their own local database

**Current Configuration:**
- Database: `jaddid_db`
- User: `postgres`
- Password: `` (change for security)
- Host: `localhost`
- Port: `5432`

### Installation & Setup

```bash
# 1. Navigate to project directory
cd "jaddid-backend"

# 2. Activate virtual environment
.\env\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
# Copy .env.example to .env and configure

# 5. Create database (use pgAdmin or psql)
# See DATABASE_SETUP.md for detailed instructions

# 6. Run migrations
cd jaddid
python manage.py makemigrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Run development server
python manage.py runserver
```

### API Documentation

Once the server is running, access interactive API documentation:
- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **JSON Schema**: http://localhost:8000/swagger.json

### File Structure

```
jaddid-backend/
├── jaddid/
│   ├── accounts/              # User management app
│   ├── marketplace/           # NEW: Marketplace app
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py          # Admin panel configurations
│   │   ├── apps.py
│   │   ├── models.py         # 8 core models
│   │   ├── serializers.py    # 10 serializers
│   │   ├── views.py          # 7 viewsets with actions
│   │   ├── urls.py           # URL routing
│   │   └── permissions.py    # Custom permissions
│   ├── jaddid/               # Project settings
│   │   ├── settings.py       # Updated with marketplace
│   │   ├── urls.py           # Updated with API routes
│   │   └── ...
│   └── manage.py
├── env/                      # Virtual environment
├── .env                      # Environment variables (DO NOT COMMIT)
├── .env.example             # Example environment file
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── DATABASE_SETUP.md        # Database setup guide
└── database_setup.sql       # SQL setup script
```

### Testing

```bash
# Run Django checks
python manage.py check

# Test database connection
python manage.py check --database default

# Run tests (when implemented)
python manage.py test marketplace
```

### Next Steps for Team

1. **Create Database**: Follow DATABASE_SETUP.md
2. **Run Migrations**: Apply database schema
3. **Create Superuser**: For admin panel access
4. **Test Endpoints**: Use Swagger UI
5. **Integrate Frontend**: Connect React/Vue frontend
6. **Add Authentication**: Implement JWT endpoints in accounts app

### Git Workflow

```bash
# Pull latest changes
git pull origin main

# Create feature branch
git checkout -b feature/marketplace-integration

# Add marketplace changes
git add jaddid/marketplace/
git add jaddid/jaddid/settings.py
git add jaddid/jaddid/urls.py
git add .env.example
git add DATABASE_SETUP.md

# Commit changes
git commit -m "Add marketplace app with full CRUD functionality"

# Push to GitHub
git push origin feature/marketplace-integration
```

**Important**: Never commit:
- `.env` file
- Database files
- `__pycache__` directories
- Migration files (discuss with team first)

---

## Arabic Documentation - التوثيق العربي

### نظرة عامة
تطبيق **سوق جديد** هو تطبيق Django REST Framework شامل مصمم لبيع وشراء المواد القابلة لإعادة التدوير. يوفر حل سوق متكامل مع قوائم المنتجات والطلبات والمراجعات والرسائل وميزات الإبلاغ.

### الميزات المنفذة

#### 1. **النماذج** (8 نماذج أساسية)

##### نموذج الفئة (Category)
- هيكل فئات هرمي لتنظيم المواد القابلة لإعادة التدوير
- دعم العلاقات الأب-الابن
- دعم ثنائي اللغة (عربي وإنجليزي)
- دعم الأيقونات/الصور للفئات

##### نموذج المنتج (Product)
- قائمة منتجات كاملة مع دعم ثنائي اللغة
- خيارات حالة متعددة (جديد، شبه جديد، جيد، مقبول، ضعيف)
- إدارة الحالة (مسودة، نشط، مباع، محجوز، محذوف)
- إدارة الأسعار والكميات
- الموقع مع إحداثيات GPS (خط العرض/خط الطول)
- عدادات المشاهدة والمفضلة
- تتبع تاريخ النشر التلقائي

##### نموذج صور المنتج (ProductImage)
- صور متعددة لكل منتج
- تحديد الصورة الأساسية
- دعم ترتيب الصور
- تنظيم تلقائي حسب التاريخ

##### نموذج المفضلة (Favorite)
- وظيفة قائمة الرغبات/المفضلة للمستخدم
- قيد فريد لكل مزيج مستخدم-منتج
- بحث سريع مع فهارس قاعدة البيانات

##### نموذج الطلب (Order)
- نظام إدارة طلبات كامل
- أرقام طلبات فريدة يتم إنشاؤها تلقائيًا
- تتبع حالة الطلب (معلق، مؤكد، قيد التنفيذ، مكتمل، ملغى، مسترد)
- تتبع حالة الدفع (غير مدفوع، مدفوع، جزئي)
- حساب السعر الإجمالي تلقائيًا
- دعم عنوان التوصيل

##### نموذج المراجعة (Review)
- نظام تقييم 5 نجوم
- مؤشر الشراء المؤكد
- نظام موافقة المسؤول
- حقول العنوان والتعليق
- مرتبط بالطلبات للتحقق من الشراء

##### نموذج الرسالة (Message)
- مراسلة مباشرة بين المشترين والبائعين
- محادثات خاصة بالمنتج
- تتبع حالة المقروءة/غير المقروءة
- موضوع ونص الرسالة

##### نموذج الإبلاغ (Report)
- نظام إدارة المحتوى
- أسباب إبلاغ متعددة (بريد مزعج، غير مناسب، احتيال، مكرر، أخرى)
- تتبع الحالة (معلق، قيد المراجعة، محلول، مرفوض)
- ملاحظات المسؤول وتتبع الحل

#### 2. **المسلسلات** (10 مسلسلات)
- **CategorySerializer**: بيانات الفئة الكاملة مع الفئات الفرعية
- **ProductListSerializer**: خفيف لعروض القائمة
- **ProductDetailSerializer**: معلومات المنتج الكاملة
- **ProductCreateUpdateSerializer**: إنشاء/تعديل المنتج مع تحميل الصور
- **ProductImageSerializer**: إدارة الصور
- **FavoriteSerializer**: إدارة قائمة الرغبات
- **OrderSerializer**: معالجة الطلبات
- **ReviewSerializer**: تقديم المراجعة
- **MessageSerializer**: وظيفة المراسلة
- **ReportSerializer**: الإبلاغ عن المحتوى

#### 3. **مجموعات العرض ونقاط نهاية API** (7 مجموعات)

##### مجموعة عرض الفئات (CategoryViewSet)
- الحصول على جميع الفئات
- تفاصيل الفئة
- هيكل شجرة الفئات
- المنتجات في الفئة
- إنشاء/تحديث/حذف الفئة (للمسؤول)

##### مجموعة عرض المنتجات (ProductViewSet)
- قائمة جميع المنتجات النشطة
- تفاصيل المنتج (يزيد عدد المشاهدات)
- منتجات المستخدم الخاصة
- إنشاء/تحديث/حذف المنتج
- إضافة/إزالة المفضلة
- مراجعات المنتج
- نشر منتج مسودة

**التصفية والبحث:**
- التصفية حسب: الفئة، الحالة، الحالة، البائع، نطاق السعر
- البحث في: العنوان، الوصف، الموقع
- الترتيب حسب: السعر، تاريخ الإنشاء، عدد المشاهدات، عدد المفضلة

##### مجموعة عرض المفضلة (FavoriteViewSet)
- مفضلات المستخدم
- إضافة إلى المفضلة
- إزالة من المفضلة

##### مجموعة عرض الطلبات (OrderViewSet)
- طلبات المستخدم (كمشتري أو بائع)
- الطلبات كمشتري
- الطلبات كبائع
- إنشاء طلب
- تأكيد الطلب (البائع)
- إكمال الطلب (البائع)
- إلغاء الطلب (المشتري/البائع)

##### مجموعة عرض المراجعات (ReviewViewSet)
- قائمة جميع المراجعات
- مراجعات المستخدم
- إنشاء/تحديث/حذف المراجعة

##### مجموعة عرض الرسائل (MessageViewSet)
- جميع الرسائل
- الرسائل المستلمة (صندوق الوارد)
- الرسائل المرسلة
- عدد الرسائل غير المقروءة
- إرسال رسالة
- وضع علامة مقروءة

##### مجموعة عرض التقارير (ReportViewSet)
- تقارير المستخدم (جميعها للمسؤول)
- تقارير المستخدم الخاصة
- إنشاء/تحديث تقرير

#### 4. **الأذونات**
- **IsSellerOrReadOnly**: فقط بائعي المنتجات يمكنهم تعديل منتجاتهم
- **IsOwnerOrReadOnly**: فقط أصحاب الموارد يمكنهم التعديل
- **IsAdminOrReadOnly**: فقط المسؤولون يمكنهم تعديل موارد معينة
- **IsAuthenticatedOrReadOnly**: وصول قراءة عام، كتابة مصادق عليها

#### 5. **لوحة الإدارة**
واجهات إدارة شاملة لجميع النماذج مع:
- عروض قائمة مخصصة مع حقول ذات صلة
- قدرات التصفية والبحث
- تعديل مضمن (مثل صور المنتج)
- إجراءات مخصصة (عمليات جماعية)
- حقول للقراءة فقط للبيانات التي يتم إنشاؤها من قبل النظام
- مجموعات حقول منظمة لتجربة مستخدم أفضل

#### 6. **ميزات قاعدة البيانات**
- **الفهارس**: فهارس استراتيجية للأداء
- **قيود فريدة**: سلامة البيانات
- **المفاتيح الأجنبية**: علاقات صحيحة
- **مفاتيح UUID الأساسية**: الأمان وقابلية التوسع

### ميزات الأمان

1. **متغيرات البيئة**: البيانات الحساسة في ملف .env
2. **حماية كلمة مرور قاعدة البيانات**: كلمة المرور غير مكودة بشكل ثابت
3. **فئات الأذونات**: التحكم في الوصول القائم على الأدوار
4. **التحقق من الإدخال**: التحقق من صحة المسلسل
5. **تكوين CORS**: قيود أصل الواجهة الأمامية
6. **مصادقة JWT**: المصادقة القائمة على الرمز جاهزة

### تكوين قاعدة البيانات

#### إعداد التعاون الجماعي
يستخدم المشروع PostgreSQL مع التكوين الآمن التالي:

**لأعضاء الفريق:**
1. نسخ `.env.example` إلى `.env`
2. تحديث بيانات اعتماد قاعدة البيانات لتتناسب مع الإعداد المحلي الخاص بك
3. لا تلتزم أبدًا بملف `.env` في Git
4. كل عضو في الفريق يستخدم قاعدة البيانات المحلية الخاصة به

**التكوين الحالي:**
- قاعدة البيانات: `jaddid_db`
- المستخدم: `postgres`
- كلمة المرور: `` (قم بتغييرها للأمان)
- المضيف: `localhost`
- المنفذ: `5432`

### التثبيت والإعداد

```bash
# 1. الانتقال إلى دليل المشروع
cd "jaddid-backend"

# 2. تفعيل البيئة الافتراضية
.\env\Scripts\Activate.ps1

# 3. تثبيت التبعيات
pip install -r requirements.txt

# 4. إعداد متغيرات البيئة
# نسخ .env.example إلى .env والتكوين

# 5. إنشاء قاعدة البيانات (استخدام pgAdmin أو psql)
# راجع DATABASE_SETUP.md للحصول على تعليمات مفصلة

# 6. تشغيل الترحيلات
cd jaddid
python manage.py makemigrations
python manage.py migrate

# 7. إنشاء مستخدم خارق
python manage.py createsuperuser

# 8. تشغيل خادم التطوير
python manage.py runserver
```

### توثيق API

بمجرد تشغيل الخادم، قم بالوصول إلى توثيق API التفاعلي:
- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/

### الخطوات التالية للفريق

1. **إنشاء قاعدة البيانات**: اتبع DATABASE_SETUP.md
2. **تشغيل الترحيلات**: تطبيق مخطط قاعدة البيانات
3. **إنشاء مستخدم خارق**: للوصول إلى لوحة الإدارة
4. **اختبار نقاط النهاية**: استخدام Swagger UI
5. **دمج الواجهة الأمامية**: ربط الواجهة الأمامية React/Vue
6. **إضافة المصادقة**: تنفيذ نقاط نهاية JWT في تطبيق accounts

### سير عمل Git

```bash
# سحب أحدث التغييرات
git pull origin main

# إنشاء فرع ميزة
git checkout -b feature/marketplace-integration

# إضافة تغييرات السوق
git add jaddid/marketplace/
git add jaddid/jaddid/settings.py
git add jaddid/jaddid/urls.py

# الالتزام بالتغييرات
git commit -m "Add marketplace app with full CRUD functionality"

# الدفع إلى GitHub
git push origin feature/marketplace-integration
```

**مهم**: لا تلتزم أبدًا:
- ملف `.env`
- ملفات قاعدة البيانات
- دلائل `__pycache__`

---

## Summary - الملخص

### English
This marketplace app provides a complete, production-ready solution for recyclable materials trading with:
- 8 comprehensive models
- 10 serializers with full validation
- 7 viewsets with 40+ endpoints
- Role-based permissions
- Bilingual support
- Complete admin interface
- Database optimization
- Security best practices

### العربية
يوفر تطبيق السوق هذا حلاً كاملاً وجاهزًا للإنتاج لتجارة المواد القابلة لإعادة التدوير مع:
- 8 نماذج شاملة
- 10 مسلسلات مع التحقق الكامل
- 7 مجموعات عرض مع أكثر من 40 نقطة نهاية
- أذونات قائمة على الأدوار
- دعم ثنائي اللغة
- واجهة إدارة كاملة
- تحسين قاعدة البيانات
- أفضل ممارسات الأمان

### Contact - اتصل
For questions or support, contact the development team.
للأسئلة أو الدعم، اتصل بفريق التطوير.

---

**Project**: Jaddid Recyclable Materials Marketplace
**Version**: 1.0.0
**Date**: December 2025
**Team**: Jaddid Development Team
