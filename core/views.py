from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.text import slugify

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, viewsets, filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication

# drf-spectacular uchun decorators
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from drf_spectacular.types import OpenApiTypes

from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs
from .serializers import (
    AboutSerializer,
    BlogSerializer,
    BlogCreateSerializer,
    CategorySerializer,
    SubcategorySerializer,
    ApplicationSerializer,
    ApplicationCreateSerializer,
    ApplicationCreateWithFilesSerializer,
    ApplicationUpdateSerializer,
    ApplicationImageSerializer,
    CustomRegisterSerializer,
    LoginSerializer,
    ProfileSerializer,
    UserSerializer,
    BannerSerializer,
    ContactUsSerializer
)

from hitcount.models import HitCount
from hitcount.views import HitCountMixin as HCViewMixin
from django_filters.rest_framework import DjangoFilterBackend
import requests

from django.db import models


# ===============================================
# TELEGRAM NOTIFICATION
# ===============================================
def send_telegram_message(full_name, email, theme, message, created_date):
    text = (
        f"📩 *Yangi Contact xabari!*\n\n"
        f"👤 *Foydalanuvchi:* {full_name}\n"
        f"📧 *Email:* {email}\n"
        f"📝 *Mavzu:* {theme}\n"
        f"💬 *Xabar:* {message}\n"
        f"⏰ *Yuborilgan:* {created_date.strftime('%Y-%m-%d %H:%M')}"
    )

    url = f"https://api.telegram.org/bot8417763736:AAG4188kWn4LofdFhJvSVWHDzj-NSCiOTLM/sendMessage"
    params = {
        "chat_id": -5075343219,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, params=params, timeout=5)
    except Exception as e:
        print("Telegram error:", e)


# ===============================================
# GOOGLE AUTH
# ===============================================
@extend_schema(tags=['Auth'])
class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Google orqali login qilish",
        description="Google ID Token orqali tizimga kirish",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'description': 'Google ID Token'}
                },
                'required': ['token']
            }
        },
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT
        }
    )
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        try:
            from django.conf import settings
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
            email = idinfo.get("email")
            name = idinfo.get("name")

            if not email:
                return Response({"error": "Email not found in token"}, status=400)

            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": name},
            )

            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.first_name,
                },
            })

        except Exception as e:
            return Response({"error": str(e)}, status=400)


def index(request):
    from django.conf import settings
    return render(request, "index.html", {"client_id": settings.GOOGLE_CLIENT_ID})


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


# ===============================================
# ABOUT VIEW
# ===============================================
@extend_schema(tags=['About'])
class AboutAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    @extend_schema(
        summary="About ma'lumotini olish",
        description="Platforma haqida ma'lumotni olish",
        responses={200: AboutSerializer, 404: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=404)
        serializer = AboutSerializer(about)
        return Response(serializer.data)

    @extend_schema(
        summary="About ma'lumotini yangilash",
        description="Platforma haqida ma'lumotni yangilash (admin uchun)",
        request=AboutSerializer,
        responses={200: AboutSerializer, 400: OpenApiTypes.OBJECT}
    )
    def put(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=404)

        serializer = AboutSerializer(about, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# ===============================================
# BANNER VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha bannerlarni olish",
        description="Barcha bannerlarni olish"
    ),
    retrieve=extend_schema(
        summary="Bannerni ID bo'yicha olish",
        description="Bannerni ID bo'yicha olish"
    ),
    create=extend_schema(
        summary="Yangi banner yaratish",
        description="Yangi banner yaratish (admin uchun)",
        request=BannerSerializer,
        responses={201: BannerSerializer}
    ),
    update=extend_schema(
        summary="Bannerni yangilash",
        description="Bannerni yangilash (admin uchun)",
        request=BannerSerializer,
        responses={200: BannerSerializer}
    ),
    partial_update=extend_schema(
        summary="Bannerni qisman yangilash",
        description="Bannerni qisman yangilash (admin uchun)",
        request=BannerSerializer,
        responses={200: BannerSerializer}
    ),
    destroy=extend_schema(
        summary="Bannerni o'chirish",
        description="Bannerni o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Banners'])
class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all().order_by("-created_date")
    serializer_class = BannerSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(
        summary="Faol bannerlarni olish",
        description="Faqat faol bannerlarni olish",
        responses={200: BannerSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='active')
    def active_banners(self, request):
        banners = Banner.objects.filter(is_active=True).order_by("-created_date")
        serializer = self.get_serializer(banners, many=True)
        return Response(serializer.data)


# ===============================================
# BLOG VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha bloglarni olish",
        description="Barcha bloglarni olish"
    ),
    retrieve=extend_schema(
        summary="Blogni slug bo'yicha olish",
        description="Blogni slug bo'yicha olish va view count oshirish"
    ),
    create=extend_schema(
        summary="Yangi blog yaratish",
        description="Yangi blog yaratish (admin uchun)",
        request=BlogCreateSerializer,
        responses={201: BlogSerializer}
    ),
    update=extend_schema(
        summary="Blogni yangilash",
        description="Blogni yangilash (admin uchun)",
        request=BlogSerializer,
        responses={200: BlogSerializer}
    ),
    partial_update=extend_schema(
        summary="Blogni qisman yangilash",
        description="Blogni qisman yangilash (admin uchun)",
        request=BlogSerializer,
        responses={200: BlogSerializer}
    ),
    destroy=extend_schema(
        summary="Blogni o'chirish",
        description="Blogni o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Blogs'])
class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by("-created_date")
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "slug"
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BlogCreateSerializer
        return BlogSerializer

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        title = serializer.validated_data.get("title")
        if title:
            slug = slugify(title)
            serializer.save(slug=slug)
        else:
            serializer.save()

    def retrieve(self, request, *args, **kwargs):
        blog = self.get_object()
        hit_count = HitCount.objects.get_for_object(blog)
        HCViewMixin.hit_count(request, hit_count)
        serializer = self.get_serializer(blog)
        return Response(serializer.data)


# ===============================================
# CATEGORY VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha kategoriyalarni olish",
        description="Barcha kategoriyalarni olish"
    ),
    retrieve=extend_schema(
        summary="Kategoriyani ID bo'yicha olish",
        description="Kategoriyani ID bo'yicha olish"
    ),
    create=extend_schema(
        summary="Yangi kategoriya yaratish",
        description="Yangi kategoriya yaratish (admin uchun)",
        request=CategorySerializer,
        responses={201: CategorySerializer}
    ),
    update=extend_schema(
        summary="Kategoriyani yangilash",
        description="Kategoriyani yangilash (admin uchun)",
        request=CategorySerializer,
        responses={200: CategorySerializer}
    ),
    partial_update=extend_schema(
        summary="Kategoriyani qisman yangilash",
        description="Kategoriyani qisman yangilash (admin uchun)",
        request=CategorySerializer,
        responses={200: CategorySerializer}
    ),
    destroy=extend_schema(
        summary="Kategoriyani o'chirish",
        description="Kategoriyani o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Categories'])
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


# ===============================================
# SUBCATEGORY VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha subkategoriyalarni olish",
        description="Barcha subkategoriyalarni olish"
    ),
    retrieve=extend_schema(
        summary="Subkategoriyani slug bo'yicha olish",
        description="Subkategoriyani slug bo'yicha olish"
    ),
    create=extend_schema(
        summary="Yangi subkategoriya yaratish",
        description="Yangi subkategoriya yaratish (admin uchun)",
        request=SubcategorySerializer,
        responses={201: SubcategorySerializer}
    ),
    update=extend_schema(
        summary="Subkategoriyani yangilash",
        description="Subkategoriyani yangilash (admin uchun)",
        request=SubcategorySerializer,
        responses={200: SubcategorySerializer}
    ),
    partial_update=extend_schema(
        summary="Subkategoriyani qisman yangilash",
        description="Subkategoriyani qisman yangilash (admin uchun)",
        request=SubcategorySerializer,
        responses={200: SubcategorySerializer}
    ),
    destroy=extend_schema(
        summary="Subkategoriyani o'chirish",
        description="Subkategoriyani o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Subcategories'])
class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubcategorySerializer
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "slug"
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def perform_create(self, serializer):
        slug = slugify(serializer.validated_data.get("title"))
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        slug = slugify(serializer.validated_data.get("title"))
        serializer.save(slug=slug)


# ===============================================
# APPLICATION VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha arizalarni olish",
        description="Arizalarni filter va search qilish",
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Kategoriya ID'
            ),
            OpenApiParameter(
                name='subcategory',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Subkategoriya ID'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Status',
                enum=['pending', 'accepted', 'denied']
            ),
            OpenApiParameter(
                name='region',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Viloyat'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Qidiruv (Ism, telefon, passport)'
            ),
        ],
        responses={200: ApplicationSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Arizani slug bo'yicha olish",
        description="Arizani slug bo'yicha olish",
        responses={200: ApplicationSerializer}
    ),
    create=extend_schema(
        summary="Yangi ariza yaratish",
        description="Yangi ariza yaratish (multipart/form-data)",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'full_name': {'type': 'string'},
                    'phone_number': {'type': 'string'},
                    'birth_date': {'type': 'string', 'format': 'date'},
                    'passport_number': {'type': 'string'},
                    'region': {'type': 'string'},
                    'location': {'type': 'string'},
                    'category': {'type': 'integer'},
                    'subcategory': {'type': 'integer'},
                    'description': {'type': 'string'},
                    'video': {'type': 'string', 'format': 'binary'},
                    'document': {'type': 'string', 'format': 'binary'},
                    'images': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'binary'},
                        'description': 'Rasm fayllari'
                    }
                },
                'required': [
                    'full_name', 'phone_number', 'birth_date',
                    'passport_number', 'region', 'category', 'subcategory'
                ]
            }
        },
        responses={201: ApplicationSerializer}
    ),
    update=extend_schema(
        summary="Arizani yangilash",
        description="Arizani yangilash (admin uchun)",
        request=ApplicationUpdateSerializer,
        responses={200: ApplicationSerializer}
    ),
    partial_update=extend_schema(
        summary="Arizani qisman yangilash",
        description="Arizani qisman yangilash (admin uchun)",
        request=ApplicationUpdateSerializer,
        responses={200: ApplicationSerializer}
    ),
    destroy=extend_schema(
        summary="Arizani o'chirish",
        description="Arizani o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Applications'])
class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by("-created_date")
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "slug"
    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'subcategory', 'status', 'region']
    search_fields = ['full_name', 'phone_number', 'passport_number']

    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateWithFilesSerializer
        elif self.action in ['update', 'partial_update']:
            return ApplicationUpdateSerializer
        return ApplicationSerializer

    def create(self, request, *args, **kwargs):
        # Foydalanuvchi nomidan slug yaratish
        full_name = request.data.get("full_name")
        if not full_name:
            return Response({"error": "full_name kerak"}, status=400)

        slug = slugify(full_name)
        counter = 1
        new_slug = slug

        while Application.objects.filter(slug=new_slug).exists():
            new_slug = f"{slug}-{counter}"
            counter += 1

        # Request datani to'g'ri formatlash
        data = {}
        for field in ['full_name', 'phone_number', 'birth_date', 'passport_number',
                    'region', 'location', 'category', 'subcategory', 'description']:
            data[field] = request.data.get(field)
        
        # Fayllarni qo'shamiz
        data['video'] = request.FILES.get('video')
        data['document'] = request.FILES.get('document')
        
        # Rasm fayllarini list qilamiz
        images_files = request.FILES.getlist('images')
        
        # Serializer yaratish
        serializer = self.get_serializer(data=data)
        
        # Validation
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Slug ni validated_data ga qo'shamiz
        validated_data = serializer.validated_data
        
        # Application yaratish
        application = Application.objects.create(
            slug=new_slug,
            **validated_data
        )
        
        # Rasm fayllarini saqlash
        for image_file in images_files:
            ApplicationImage.objects.create(
                application=application,
                image=image_file
            )
        
        return Response(
            ApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED
        )
    
    def perform_update(self, serializer):
        full_name = serializer.validated_data.get("full_name")
        if full_name:
            slug = slugify(full_name)
            counter = 1
            new_slug = slug
            while Application.objects.filter(slug=new_slug).exclude(pk=self.get_object().pk).exists():
                new_slug = f"{slug}-{counter}"
                counter += 1
            serializer.save(slug=new_slug)
        else:
            serializer.save()

    @extend_schema(
        summary="Arizaga bitta rasm qo'shish",
        description="Arizaga bitta rasm qo'shish (admin uchun)",
        request=ApplicationImageSerializer,
        responses={201: ApplicationImageSerializer}
    )
    @action(detail=True, methods=["post"], url_path="add-image")
    def add_image(self, request, slug=None):
        application = self.get_object()

        image_file = request.FILES.get("image")
        image_url = request.data.get("image_url")

        if not image_file and not image_url:
            return Response({"error": "image yoki image_url kiriting"}, status=400)

        serializer = ApplicationImageSerializer(
            data={"image": image_file, "image_url": image_url}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)

        return Response(serializer.data, status=201)

    @extend_schema(
        summary="Arizaga bir nechta rasm qo'shish",
        description="Arizaga bir nechta rasm qo'shish (admin uchun)",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'images': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'binary'},
                        'description': 'Rasm fayllari'
                    }
                },
                'required': ['images']
            }
        },
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'},
                    'added_count': {'type': 'integer'}
                }
            }
        }
    )
    @action(detail=True, methods=["post"], url_path="add-images")
    def add_images(self, request, slug=None):
        application = self.get_object()
        images = request.FILES.getlist("images")

        if not images:
            return Response({"error": "Rasm yuborilmadi"}, status=400)

        added = 0
        for image in images:
            ApplicationImage.objects.create(
                application=application,
                image=image
            )
            added += 1

        return Response(
            {"detail": f"{added} ta rasm qo'shildi", "added_count": added},
            status=201
        )

    @extend_schema(
        summary="Arizaning barcha rasmlarini olish",
        description="Arizaning barcha rasmlarini olish",
        responses={200: ApplicationImageSerializer(many=True)}
    )
    @action(detail=True, methods=["get"], url_path="images")
    def get_images(self, request, slug=None):
        application = self.get_object()
        serializer = ApplicationImageSerializer(application.images.all(), many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Arizaning barcha rasmlarini o'chirish",
        description="Arizaning barcha rasmlarini o'chirish (admin uchun)",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'},
                    'deleted_count': {'type': 'integer'}
                }
            }
        }
    )
    @action(detail=True, methods=["delete"], url_path="delete-all-images")
    def delete_all_images(self, request, slug=None):
        application = self.get_object()
        deleted_count, _ = application.images.all().delete()

        return Response({
            "detail": f"{deleted_count} ta rasm o'chirildi",
            "deleted_count": deleted_count
        })

    @extend_schema(
        summary="Ariza statusini o'zgartirish",
        description="Ariza statusini o'zgartirish (admin uchun)",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'enum': ['pending', 'accepted', 'denied'],
                        'description': 'Yangi status'
                    },
                    'denied_reason': {
                        'type': 'string',
                        'description': 'Rad etilgan sababi (faqat status=denied bo\'lsa)'
                    }
                },
                'required': ['status']
            }
        },
        responses={200: ApplicationSerializer}
    )
    @action(detail=True, methods=["patch"], url_path="set-status")
    def set_status(self, request, slug=None):
        application = self.get_object()
        status_value = request.data.get("status")
        denied_reason = request.data.get("denied_reason", "")

        if status_value not in ["pending", "accepted", "denied"]:
            return Response({"error": "Noto'g'ri status"}, status=400)

        application.status = status_value
        application.denied_reason = denied_reason if status_value == "denied" else ""
        application.save()

        serializer = self.get_serializer(application)
        return Response(serializer.data)


# ===============================================
# APPLICATION IMAGE VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha ariza rasmlarini olish",
        description="Barcha ariza rasmlarini olish"
    ),
    retrieve=extend_schema(
        summary="Ariza rasmini ID bo'yicha olish",
        description="Ariza rasmini ID bo'yicha olish"
    ),
    create=extend_schema(
        summary="Yangi ariza rasmini yaratish",
        description="Yangi ariza rasmini yaratish (admin uchun)",
        request=ApplicationImageSerializer,
        responses={201: ApplicationImageSerializer}
    ),
    update=extend_schema(
        summary="Ariza rasmini yangilash",
        description="Ariza rasmini yangilash (admin uchun)",
        request=ApplicationImageSerializer,
        responses={200: ApplicationImageSerializer}
    ),
    partial_update=extend_schema(
        summary="Ariza rasmini qisman yangilash",
        description="Ariza rasmini qisman yangilash (admin uchun)",
        request=ApplicationImageSerializer,
        responses={200: ApplicationImageSerializer}
    ),
    destroy=extend_schema(
        summary="Ariza rasmini o'chirish",
        description="Ariza rasmini o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Application Images'])
class ApplicationImageViewSet(viewsets.ModelViewSet):
    queryset = ApplicationImage.objects.all().order_by("-created_date")
    serializer_class = ApplicationImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


# ===============================================
# AUTH VIEWS
# ===============================================
@extend_schema(tags=['Auth'])
class RegisterView(CreateAPIView):
    serializer_class = CustomRegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Ro'yxatdan o'tish",
        description="Yangi foydalanuvchi ro'yxatdan o'tishi",
        request=CustomRegisterSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string'},
                    'access': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'email': {'type': 'string'}
                        }
                    }
                }
            }
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
            }
        }
        return Response(data, status=201)


@extend_schema(tags=['Auth'])
class LoginView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Login qilish",
        description="Email va parol orqali tizimga kirish (JWT token qaytaradi)",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string', 'format': 'password'}
                },
                'required': ['email', 'password']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string'},
                    'access': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'email': {'type': 'string'},
                            'first_name': {'type': 'string'},
                            'last_name': {'type': 'string'}
                        }
                    }
                }
            }
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=200)
        return Response(serializer.errors, status=400)


@extend_schema(tags=['Auth'])
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="JWT token yangilash",
        description="Refresh token orqali yangi access token olish",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string'}
                },
                'required': ['refresh']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'}
                }
            }
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            access_token = str(token.access_token)
            
            return Response({
                "access": access_token,
                "refresh": refresh_token
            }, status=200)
        except Exception as e:
            return Response({"error": "Yaroqsiz token"}, status=400)


@extend_schema(tags=['Auth'])
class ProfileAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Profil ma'lumotlarini olish",
        description="Foydalanuvchi profil ma'lumotlarini olish",
        responses={200: ProfileSerializer, 404: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response({"error": "Profil topilmadi"}, status=404)

    @extend_schema(
        summary="Profil ma'lumotlarini yangilash",
        description="Foydalanuvchi profil ma'lumotlarini yangilash",
        request=ProfileSerializer,
        responses={200: ProfileSerializer, 400: OpenApiTypes.OBJECT}
    )
    def put(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Profile.DoesNotExist:
            return Response({"error": "Profil topilmadi"}, status=404)


@extend_schema(tags=['Auth'])
class TestAuthView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Autentifikatsiyani test qilish",
        description="JWT token orqali autentifikatsiyani test qilish",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'email': {'type': 'string'},
                            'username': {'type': 'string'}
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        return Response({
            "message": "Autentifikatsiya muvaffaqiyatli!",
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "username": request.user.username
            }
        })


# ===============================================
# STATISTICS VIEW
# ===============================================
@extend_schema(tags=['Statistics'])
class StatisticsAPIView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Umumiy statistika",
        description="Platforma umumiy statistikasi",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total_applications': {'type': 'integer', 'description': 'Jami arizalar soni'},
                    'accepted_applications': {'type': 'integer', 'description': 'Qabul qilingan arizalar'},
                    'denied_applications': {'type': 'integer', 'description': 'Rad etilgan arizalar'},
                    'pending_applications': {'type': 'integer', 'description': 'Ko\'rib chiqilayotgan arizalar'},
                    'total_users': {'type': 'integer', 'description': 'Jami foydalanuvchilar'},
                    'total_blogs': {'type': 'integer', 'description': 'Jami bloglar'},
                    'total_categories': {'type': 'integer', 'description': 'Jami kategoriyalar'},
                    'total_subcategories': {'type': 'integer', 'description': 'Jami subkategoriyalar'},
                    'total_banners': {'type': 'integer', 'description': 'Jami bannerlar'},
                    'total_contacts': {'type': 'integer', 'description': 'Jami contact xabarlar'},
                    'unread_contacts': {'type': 'integer', 'description': 'O\'qilmagan contact xabarlar'},
                }
            }
        }
    )
    def get(self, request):
        data = {
            "total_applications": Application.objects.count(),
            "accepted_applications": Application.objects.filter(status="accepted").count(),
            "denied_applications": Application.objects.filter(status="denied").count(),
            "pending_applications": Application.objects.filter(status="pending").count(),
            "total_users": User.objects.count(),
            "total_blogs": Blog.objects.count(),
            "total_categories": Category.objects.count(),
            "total_subcategories": Subcategory.objects.count(),
            "total_banners": Banner.objects.count(),
            "total_contacts": ContactUs.objects.count(),
            "unread_contacts": ContactUs.objects.filter(is_read=False).count(),
        }
        return Response(data)


# ===============================================
# CONTACT US VIEWSET
# ===============================================
@extend_schema_view(
    list=extend_schema(
        summary="Barcha contact xabarlarini olish",
        description="Barcha contact xabarlarini olish (admin uchun)",
        responses={200: ContactUsSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Contact xabarni ID bo'yicha olish",
        description="Contact xabarni ID bo'yicha olish (admin uchun)",
        responses={200: ContactUsSerializer}
    ),
    create=extend_schema(
        summary="Yangi contact xabar yaratish",
        description="Yangi contact xabar yaratish",
        request=ContactUsSerializer,
        responses={201: ContactUsSerializer}
    ),
    update=extend_schema(
        summary="Contact xabarni yangilash",
        description="Contact xabarni yangilash (admin uchun)",
        request=ContactUsSerializer,
        responses={200: ContactUsSerializer}
    ),
    partial_update=extend_schema(
        summary="Contact xabarni qisman yangilash",
        description="Contact xabarni qisman yangilash (admin uchun)",
        request=ContactUsSerializer,
        responses={200: ContactUsSerializer}
    ),
    destroy=extend_schema(
        summary="Contact xabarni o'chirish",
        description="Contact xabarni o'chirish (admin uchun)"
    )
)
@extend_schema(tags=['Contact Us'])
class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.all().order_by("-created_date")
    serializer_class = ContactUsSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()

        # Telegramga yuborish
        send_telegram_message(
            full_name=contact.full_name,
            email=contact.email,
            theme=contact.theme,
            message=contact.message,
            created_date=contact.created_date
        )

        return Response(serializer.data, status=201)

    @extend_schema(
        summary="Xabarni o'qilgan deb belgilash",
        description="Xabarni o'qilgan deb belgilash (admin uchun)",
        responses={200: ContactUsSerializer}
    )
    @action(detail=True, methods=['patch'], url_path='mark-read')
    def mark_as_read(self, request, pk=None):
        msg = self.get_object()
        msg.is_read = True
        msg.save()
        serializer = self.get_serializer(msg)
        return Response(serializer.data)


# ===============================================
# FILTER VIEWS
# ===============================================
@extend_schema(
    methods=['GET'],
    summary="Kategoriya bo'yicha arizalarni olish",
    description="Kategoriya ID bo'yicha arizalarni olish",
    responses={200: ApplicationSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def applications_by_category(request, category_id):
    apps = Application.objects.filter(category_id=category_id).order_by('-created_date')
    serializer = ApplicationSerializer(apps, many=True)
    return Response(serializer.data)


@extend_schema(
    methods=['GET'],
    summary="Subkategoriya bo'yicha arizalarni olish",
    description="Subkategoriya ID bo'yicha arizalarni olish",
    responses={200: ApplicationSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def applications_by_subcategory(request, subcategory_id):
    apps = Application.objects.filter(subcategory_id=subcategory_id).order_by('-created_date')
    serializer = ApplicationSerializer(apps, many=True)
    return Response(serializer.data)


@extend_schema(
    methods=['GET'],
    summary="Arizalarni filter qilish",
    description="Arizalarni turli parametrlar bo'yicha filter qilish",
    parameters=[
        OpenApiParameter(
            name='category',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Kategoriya ID'
        ),
        OpenApiParameter(
            name='subcategory',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Subkategoriya ID'
        ),
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Status',
            enum=['pending', 'accepted', 'denied']
        ),
        OpenApiParameter(
            name='region',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Viloyat'
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Qidiruv (Ism, telefon, passport)'
        ),
    ],
    responses={200: ApplicationSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def filter_applications(request):
    category_id = request.GET.get('category')
    subcategory_id = request.GET.get('subcategory')
    status = request.GET.get('status')
    region = request.GET.get('region')
    search = request.GET.get('search')

    queryset = Application.objects.all()

    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if subcategory_id:
        queryset = queryset.filter(subcategory_id=subcategory_id)
    if status:
        queryset = queryset.filter(status=status)
    if region:
        queryset = queryset.filter(region=region)
    if search:
        queryset = queryset.filter(
            models.Q(full_name__icontains=search) |
            models.Q(phone_number__icontains=search) |
            models.Q(passport_number__icontains=search)
        )

    serializer = ApplicationSerializer(queryset, many=True)
    return Response(serializer.data)