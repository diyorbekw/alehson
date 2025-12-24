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
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs
from .serializers import (
    AboutSerializer, BlogSerializer, BlogCreateSerializer,
    CategorySerializer, SubcategorySerializer, ApplicationSerializer, 
    ApplicationCreateSerializer, ApplicationCreateSerializerWithFiles,
    ApplicationUpdateSerializer, ApplicationImageSerializer, RegisterSerializer, 
    LoginSerializer, ProfileSerializer, UserSerializer, BannerSerializer, 
    ContactUsSerializer
)

from hitcount.models import HitCount
from hitcount.views import HitCountMixin as HCViewMixin
from rest_framework import filters
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
class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Google orqali login qilish",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "token": openapi.Schema(type=openapi.TYPE_STRING, description="Google ID Token"),
            },
            required=["token"],
        ),
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
class AboutAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="About ma'lumotini olish",
        responses={200: AboutSerializer, 404: "Ma'lumot topilmadi"}
    )
    def get(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=404)
        serializer = AboutSerializer(about)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="About ma'lumotini yangilash (multipart/form-data)",
        request_body=AboutSerializer,
        responses={200: AboutSerializer, 400: "Xatolik"}
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
class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all().order_by("-created_date")
    serializer_class = BannerSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @swagger_auto_schema(
        operation_description="Banner yaratish (multipart/form-data)",
        request_body=BannerSerializer,
        responses={201: BannerSerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Banner rasmi",
                type=openapi.TYPE_FILE,
                required=True
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Banner yangilash (multipart/form-data)",
        request_body=BannerSerializer,
        responses={200: BannerSerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Banner rasmi",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='active')
    @swagger_auto_schema(
        operation_description="Faol bannerlarni olish",
        responses={200: BannerSerializer(many=True)}
    )
    def active_banners(self, request):
        banners = Banner.objects.filter(is_active=True).order_by("-created_date")
        serializer = self.get_serializer(banners, many=True)
        return Response(serializer.data)


# ===============================================
# BLOG VIEWSET
# ===============================================
class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by("-created_date")
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "slug"
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BlogCreateSerializer
        return BlogSerializer

    @swagger_auto_schema(
        operation_description="Blog yaratish (multipart/form-data)",
        request_body=BlogCreateSerializer,
        responses={201: BlogSerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Blog rasmi",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)

    @swagger_auto_schema(
        operation_description="Blog yangilash (multipart/form-data)",
        request_body=BlogSerializer,
        responses={200: BlogSerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Blog rasmi",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        title = serializer.validated_data.get("title")
        if title:
            slug = slugify(title)
            serializer.save(slug=slug)
        else:
            serializer.save()

    @swagger_auto_schema(
        operation_description="Blogni olish va view count oshirish",
        responses={200: BlogSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        blog = self.get_object()
        hit_count = HitCount.objects.get_for_object(blog)
        HCViewMixin.hit_count(request, hit_count)
        serializer = self.get_serializer(blog)
        return Response(serializer.data)


# ===============================================
# CATEGORY VIEWSET
# ===============================================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @swagger_auto_schema(
        operation_description="Category yaratish (multipart/form-data)",
        request_body=CategorySerializer,
        responses={201: CategorySerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Kategoriya rasmi",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Category yangilash (multipart/form-data)",
        request_body=CategorySerializer,
        responses={200: CategorySerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Kategoriya rasmi",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


# ===============================================
# SUBCATEGORY VIEWSET
# ===============================================
class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubcategorySerializer
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
class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by("-created_date")
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "slug"
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'subcategory', 'status', 'region']
    search_fields = ['full_name', 'phone_number', 'passport_number']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializerWithFiles
        elif self.action in ['update', 'partial_update']:
            return ApplicationUpdateSerializer
        return ApplicationSerializer

    @swagger_auto_schema(
        operation_description="Ariza yaratish (multipart/form-data) - video, document va images bilan",
        request_body=ApplicationCreateSerializerWithFiles,
        responses={201: ApplicationSerializer},
        manual_parameters=[
            openapi.Parameter(
                'passport_photo',
                openapi.IN_FORM,
                description="Pasport rasm",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'passport_scan',
                openapi.IN_FORM,
                description="Pasport skan",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'video',
                openapi.IN_FORM,
                description="Video fayl",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'document',
                openapi.IN_FORM,
                description="Hujjat fayl",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'images[]',
                openapi.IN_FORM,
                description="Qo'shimcha rasmlar (multiple)",
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                required=False,
                collection_format='multi'
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        full_name = serializer.validated_data.get("full_name")
        slug = slugify(full_name)
        counter = 1
        new_slug = slug
        
        while Application.objects.filter(slug=new_slug).exists():
            new_slug = f"{slug}-{counter}"
            counter += 1
            
        application = serializer.save(slug=new_slug)
        return Response(ApplicationSerializer(application).data, status=201)

    @swagger_auto_schema(
        operation_description="Ariza yangilash (multipart/form-data)",
        request_body=ApplicationUpdateSerializer,
        responses={200: ApplicationSerializer},
        manual_parameters=[
            openapi.Parameter(
                'passport_photo',
                openapi.IN_FORM,
                description="Pasport rasm",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'passport_scan',
                openapi.IN_FORM,
                description="Pasport skan",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'video',
                openapi.IN_FORM,
                description="Video fayl",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'document',
                openapi.IN_FORM,
                description="Hujjat fayl",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

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

    @action(detail=True, methods=["post"], url_path="add-image")
    @swagger_auto_schema(
        operation_description="Arizaga rasm qo'shish (multipart/form-data)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "image": openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Rasm fayli"
                )
            },
            required=["image"]
        ),
        responses={201: ApplicationImageSerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Rasm fayli",
                type=openapi.TYPE_FILE,
                required=True
            ),
        ]
    )
    def add_image(self, request, slug=None):
        application = self.get_object()
        serializer = ApplicationImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(application=application)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["patch"], url_path="set-status")
    @swagger_auto_schema(
        operation_description="Ariza statusini o'zgartirish",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["pending", "accepted", "denied"],
                    description="Yangi status"
                ),
                "denied_reason": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Rad etish sababi (faqat denied statusida)"
                )
            },
            required=["status"]
        ),
        responses={200: "Status yangilandi"}
    )
    def set_status(self, request, slug=None):
        application = self.get_object()
        status_value = request.data.get("status")
        denied_reason = request.data.get("denied_reason", "")

        if status_value not in ["pending", "accepted", "denied"]:
            return Response({"error": "Noto'g'ri status qiymati"}, status=400)

        application.status = status_value
        application.denied_reason = denied_reason if status_value == "denied" else ""
        application.save()

        return Response({
            "detail": "Status yangilandi",
            "status": application.status,
            "denied_reason": application.denied_reason
        })
        
# ===============================================
# APPLICATION IMAGE VIEWSET
# ===============================================
class ApplicationImageViewSet(viewsets.ModelViewSet):
    queryset = ApplicationImage.objects.all().order_by("-created_date")
    serializer_class = ApplicationImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @swagger_auto_schema(
        operation_description="Ariza rasmini yaratish (multipart/form-data)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "application": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Ariza ID"
                ),
                "image": openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Rasm fayli"
                )
            },
            required=["application", "image"]
        ),
        responses={201: ApplicationImageSerializer},
        manual_parameters=[
            openapi.Parameter(
                'image',
                openapi.IN_FORM,
                description="Rasm fayli",
                type=openapi.TYPE_FILE,
                required=True
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


# ===============================================
# AUTH VIEWS
# ===============================================
class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Ro'yxatdan o'tish",
        request_body=RegisterSerializer,
        responses={201: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                "access": openapi.Schema(type=openapi.TYPE_STRING),
                "user": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "email": openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            }
        )}
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


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Login qilish (JWT token qaytaradi)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
            required=["email", "password"],
        ),
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=200)
        return Response(serializer.errors, status=400)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="JWT token yangilash",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["refresh"],
        ),
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


class ProfileAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Profil ma'lumotlarini olish",
        responses={200: ProfileSerializer, 404: "Profil topilmadi"}
    )
    def get(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response({"error": "Profil topilmadi"}, status=404)

    @swagger_auto_schema(
        operation_description="Profil ma'lumotlarini yangilash (multipart/form-data)",
        request_body=ProfileSerializer,
        responses={200: ProfileSerializer, 400: "Xatolik"},
        manual_parameters=[
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description="Profil rasmi",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ]
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


class TestAuthView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Autentifikatsiyani test qilish",
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(type=openapi.TYPE_STRING),
                "user": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "email": openapi.Schema(type=openapi.TYPE_STRING),
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            }
        )}
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
class StatisticsAPIView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Umumiy statistika",
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "total_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami arizalar soni"),
                "accepted_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Qabul qilingan arizalar"),
                "denied_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Rad etilgan arizalar"),
                "pending_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Ko'rib chiqilayotgan arizalar"),
                "total_users": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami foydalanuvchilar"),
                "total_blogs": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami bloglar"),
                "total_categories": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami kategoriyalar"),
                "total_subcategories": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami subkategoriyalar"),
                "total_banners": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami bannerlar"),
                "total_contacts": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami contact xabarlar"),
                "unread_contacts": openapi.Schema(type=openapi.TYPE_INTEGER, description="O'qilmagan contact xabarlar"),
            }
        )}
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
class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.all().order_by("-created_date")
    serializer_class = ContactUsSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @swagger_auto_schema(
        operation_description="Contact xabar yaratish",
        request_body=ContactUsSerializer,
        responses={201: ContactUsSerializer}
    )
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

    @action(detail=True, methods=['patch'], url_path='mark-read')
    @swagger_auto_schema(
        operation_description="Xabarni o'qilgan deb belgilash",
        responses={200: ContactUsSerializer}
    )
    def mark_as_read(self, request, pk=None):
        msg = self.get_object()
        msg.is_read = True
        msg.save()
        serializer = self.get_serializer(msg)
        return Response(serializer.data)


# ===============================================
# FILTER VIEWS
# ===============================================
@api_view(['GET'])
@permission_classes([AllowAny])
@swagger_auto_schema(
    operation_description="Kategoriya bo'yicha arizalarni olish",
    responses={200: ApplicationSerializer(many=True)}
)
def applications_by_category(request, category_id):
    apps = Application.objects.filter(category_id=category_id).order_by('-created_date')
    serializer = ApplicationSerializer(apps, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
@swagger_auto_schema(
    operation_description="Subkategoriya bo'yicha arizalarni olish",
    responses={200: ApplicationSerializer(many=True)}
)
def applications_by_subcategory(request, subcategory_id):
    apps = Application.objects.filter(subcategory_id=subcategory_id).order_by('-created_date')
    serializer = ApplicationSerializer(apps, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
@swagger_auto_schema(
    operation_description="Arizalarni filter qilish",
    manual_parameters=[
        openapi.Parameter(
            'category',
            openapi.IN_QUERY,
            description="Kategoriya ID",
            type=openapi.TYPE_INTEGER
        ),
        openapi.Parameter(
            'subcategory',
            openapi.IN_QUERY,
            description="Subkategoriya ID",
            type=openapi.TYPE_INTEGER
        ),
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Status",
            type=openapi.TYPE_STRING,
            enum=['pending', 'accepted', 'denied']
        ),
        openapi.Parameter(
            'region',
            openapi.IN_QUERY,
            description="Viloyat",
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'search',
            openapi.IN_QUERY,
            description="Qidiruv (Ism, telefon, passport)",
            type=openapi.TYPE_STRING
        ),
    ],
    responses={200: ApplicationSerializer(many=True)}
)
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