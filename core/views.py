from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.text import slugify

from google.oauth2 import id_token
from google.auth.transport import requests

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status as drf_status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile
from .serializers import (
    AboutSerializer, BlogSerializer, CategorySerializer,
    SubcategorySerializer, ApplicationSerializer, ApplicationImageSerializer,
    RegisterSerializer, LoginSerializer, ProfileSerializer, UserSerializer
)

from hitcount.models import HitCount
from hitcount.views import HitCountMixin as HCViewMixin


# ---------------- Google Auth ----------------
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
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
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


# ---------------- About ----------------
class AboutAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]

    def get(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=404)
        serializer = AboutSerializer(about)
        return Response(serializer.data)

    def put(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=404)

        serializer = AboutSerializer(about, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# ---------------- Blog ----------------
class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by("-created_date")
    serializer_class = BlogSerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)

    def retrieve(self, request, *args, **kwargs):
        blog = self.get_object()
        hit_count = HitCount.objects.get_for_object(blog)
        HCViewMixin.hit_count(request, hit_count)
        serializer = self.get_serializer(blog)
        return Response(serializer.data)


# ---------------- Category & Subcategory ----------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubcategorySerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)


# ---------------- Application ----------------
class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by("-id")
    serializer_class = ApplicationSerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        full_name = serializer.validated_data.get("full_name")
        slug = slugify(full_name)
        counter, new_slug = 1, slug
        while Application.objects.filter(slug=new_slug).exists():
            new_slug = f"{slug}-{counter}"
            counter += 1
        serializer.save(slug=new_slug)

    def perform_update(self, serializer):
        full_name = serializer.validated_data.get("full_name")
        slug = slugify(full_name)
        counter, new_slug = 1, slug
        while Application.objects.filter(slug=new_slug).exclude(pk=self.get_object().pk).exists():
            new_slug = f"{slug}-{counter}"
            counter += 1
        serializer.save(slug=new_slug)

    @action(detail=True, methods=["post"], url_path="add-image")
    def add_image(self, request, slug=None):
        application = self.get_object()
        serializer = ApplicationImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(application=application)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["patch"], url_path="set-status")
    def set_status(self, request, slug=None):
        application = self.get_object()
        status_value = request.data.get("status")
        denied_reason = request.data.get("denied_reason", "")

        if status_value not in ["pending", "accepted", "denied"]:
            return Response(
                {"error": "Noto‘g‘ri status qiymati"},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        application.status = status_value
        if status_value == "denied":
            application.denied_reason = denied_reason
        else:
            application.denied_reason = ""

        # faqat kerakli fieldlarni saqlaymiz → subcategory validation ishlamaydi
        application.save(update_fields=["status", "denied_reason"])

        return Response(
            {"detail": "Status yangilandi", "status": application.status, "denied_reason": application.denied_reason},
            status=drf_status.HTTP_200_OK
        )


# ---------------- ApplicationImage ----------------
class ApplicationImageViewSet(viewsets.ModelViewSet):
    queryset = ApplicationImage.objects.all()
    serializer_class = ApplicationImageSerializer
    permission_classes = [AllowAny]


# ---------------- Register / Login ----------------
class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

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

    def get(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response({"error": "Profil topilmadi"}, status=404)

    @swagger_auto_schema(
        request_body=ProfileSerializer,   # <-- mana shu joyi muhim
        responses={200: ProfileSerializer}
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
    
    def get(self, request):
        return Response({
            "message": "Autentifikatsiya muvaffaqiyatli!",
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "username": request.user.username
            }
        })
        
class StatisticsAPIView(APIView):
    permission_classes = [AllowAny]  # agar faqat adminlarga bo‘lsin desang -> [IsAdminUser]
    @swagger_auto_schema(
        operation_description="Umumiy statistika",
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "total_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami arizalar soni"),
                "accepted_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Qabul qilingan arizalar"),
                "denied_applications": openapi.Schema(type=openapi.TYPE_INTEGER, description="Rad etilgan arizalar"),
                "total_users": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami foydalanuvchilar"),
                "total_blogs": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami bloglar"),
                "total_categories": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami kategoriyalar"),
                "total_subcategories": openapi.Schema(type=openapi.TYPE_INTEGER, description="Jami subkategoriyalar"),
            }
        )}
    )
    def get(self, request):
        data = {
            "total_applications": Application.objects.count(),
            "accepted_applications": Application.objects.filter(status="accepted").count(),
            "denied_applications": Application.objects.filter(status="denied").count(),
            "total_users": User.objects.count(),
            "total_blogs": Blog.objects.count(),
            "total_categories": Category.objects.count(),
            "total_subcategories": Subcategory.objects.count(),
        }
        return Response(data)