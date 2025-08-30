from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.text import slugify

from google.oauth2 import id_token
from google.auth.transport import requests

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.decorators import api_view

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import About, Blog, Category, Subcategory, Application, ApplicationImage
from .serializers import AboutSerializer, BlogSerializer, CategorySerializer, SubcategorySerializer, ApplicationSerializer, ApplicationImageSerializer, RegisterSerializer, LoginSerializer

from hitcount.models import HitCount
from hitcount.views import HitCountMixin as HCViewMixin

class GoogleAuthView(APIView):
    @swagger_auto_schema(
        operation_description="Google orqali login qilish",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "token": openapi.Schema(type=openapi.TYPE_STRING, description="Google ID Token"),
            },
            required=["token"],
        ),
        responses={200: openapi.Response(
            description="JWT tokens qaytaradi",
            examples={
                "application/json": {
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...",
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...",
                    "user": {
                        "id": 1,
                        "email": "user@gmail.com",
                        "name": "User Name"
                    }
                }
            }
        )},
    )
    def post(self, request):
        token = request.data.get("token")
        print(f"Received token: {token}")  # Debug uchun
        
        if not token:
            return Response({"error": "Token required"}, status=400)

        try:
            # Google tokenni tekshirish
            idinfo = id_token.verify_oauth2_token(token, requests.Request())
            print(f"Google response: {idinfo}")  # Debug uchun
            
            email = idinfo.get("email")
            name = idinfo.get("name")

            if not email:
                return Response({"error": "Email not found in token"}, status=400)

            # User yaratish yoki olish
            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": name},
            )
            
            print(f"User {'created' if created else 'found'}: {user.username}")  # Debug uchun

            # JWT token yaratish
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
            print(f"Error: {str(e)}")  # Debug uchun
            return Response({"error": str(e)}, status=400)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

def index(request):
    return render(request, 'index.html')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})

# views.py
class AboutAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_description="About ma'lumotlarini olish",
        responses={200: AboutSerializer}
    )
    def get(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AboutSerializer(about)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="About ma'lumotlarini yangilash",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'main_title': openapi.Schema(type=openapi.TYPE_STRING, description="Asosiy sarlavha"),
                'hero_title': openapi.Schema(type=openapi.TYPE_STRING, description="Hero sarlavha"),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description="Tavsif"),
                'main_image': openapi.Schema(type=openapi.TYPE_FILE, description="Asosiy rasm (ixtiyoriy)"),
            },
            required=['main_title', 'hero_title', 'description']
        ),
        responses={
            200: AboutSerializer,
            400: "Xato ma'lumotlar",
            404: "Ma'lumot topilmadi"
        }
    )
    def put(self, request):
        about = About.objects.first()
        if not about:
            return Response({"detail": "About ma'lumot topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        if 'main_image' in request.FILES:
            data['main_image'] = request.FILES['main_image']

        serializer = AboutSerializer(about, data=data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by("-created_date")
    serializer_class = BlogSerializer
    lookup_field = "slug"

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


    
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubcategorySerializer
    lookup_field = "slug"  

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        title = serializer.validated_data.get("title")
        slug = slugify(title)
        serializer.save(slug=slug)
        
class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by("-id")
    serializer_class = ApplicationSerializer
    lookup_field = "slug"

    def perform_create(self, serializer):
        full_name = serializer.validated_data.get("full_name")
        slug = slugify(full_name)
        # slug unique qilish
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
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationImageViewSet(viewsets.ModelViewSet):
    queryset = ApplicationImage.objects.all()
    serializer_class = ApplicationImageSerializer
    
class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer

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
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
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
        responses={
            200: openapi.Response(
                description="JWT tokenlar va user ma’lumotlari",
                examples={
                    "application/json": {
                        "refresh": "xxx.yyy.zzz",
                        "access": "aaa.bbb.ccc",
                        "user": {
                            "id": 1,
                            "email": "user@gmail.com"
                        }
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=200)
        return Response(serializer.errors, status=400)

regions = [
  {
    "id": 1,
    "title": "Andijon",
    "items": [
      "Andijon","Asaka","Baliqchi","Boʻz","Buloqboshi","Izboskan","Jalaquduq",
      "Xoʻjaobod","Qoʻrgʻontepa","Marhamat","Oltinkoʻl","Paxtaobod","Shahrixon","Ulugʻnor"
    ],
  },
  {
    "id": 2,
    "title": "Buxoro",
    "items": [
      "Olot","Buxoro","Gʻijduvon","Jondor","Kogon","Qorakoʻl","Qorovulbozor",
      "Peshku","Romitan","Shofirkon","Vobkent"
    ],
  },
  {
    "id": 3,
    "title": "Fargʻona",
    "items": [
      "Oltiariq","Bagʻdod","Beshariq","Buvayda","Dangʻara","Fargʻona","Furqat",
      "Qoʻshtepa","Quva","Rishton","Soʻx","Toshloq","Uchkoʻprik","Oʻzbekiston","Yozyovon","Quvasoy"
    ],
  },
  {
    "id": 4,
    "title": "Jizzax",
    "items": [
      "Arnasoy","Baxmal","Doʻstlik","Forish","Gʻallaorol","Sharof Rashidov","Mirzachoʻl",
      "Paxtakor","Yangiobod","Zomin","Zafarobod","Zarbdor"
    ],
  },
  {
    "id": 5,
    "title": "Xorazm",
    "items": [
      "Bogʻot","Gurlan","Xonqa","Hazorasp","Xiva","Qoʻshkoʻpir","Shovot","Urganch",
      "Yangiariq","Yangibozor","Tuproqqalʼa"
    ],
  },
  {
    "id": 6,
    "title": "Namangan",
    "items": [
      "Chortoq","Chust","Kosonsoy","Mingbuloq","Namangan","Norin","Pop",
      "Toʻraqoʻrgʻon","Uchqoʻrgʻon","Uychi","Yangiqoʻrgʻon"
    ],
  },
  {
    "id": 7,
    "title": "Navoiy",
    "items": ["Konimex","Karmana","Qiziltepa","Xatirchi","Navbahor","Nurota","Tomdi","Uchquduq"],
  },
  {
    "id": 8,
    "title": "Qashqadaryo",
    "items": [
      "Chiroqchi","Dehqonobod","Gʻuzor","Qamashi","Qarshi","Koson","Kasbi","Kitob",
      "Mirishkor","Muborak","Nishon","Shahrisabz","Yakkabogʻ","Koʻkdala"
    ],
  },
  {
    "id": 9,
    "title": "Qoraqalpogʻiston",
    "items": [
      "Amudaryo","Beruniy","Chimboy","Ellikqalʼa","Kegeyli","Moʻynoq","Nukus",
      "Qanlikoʻl","Qoʻngʻirot","Qoraoʻzak","Shumanay","Taxtakoʻpir","Toʻrtkoʻl",
      "Xoʻjayli","Taxiatosh","Boʻzatov"
    ],
  },
  {
    "id": 10,
    "title": "Samarqand",
    "items": [
      "Bulungʻur","Ishtixon","Jomboy","Kattaqoʻrgʻon","Qoʻshrabot","Narpay","Nurobod",
      "Oqdaryo","Paxtachi","Payariq","Pastdargʻom","Samarqand","Toyloq","Urgut"
    ],
  },
  {
    "id": 11,
    "title": "Sirdaryo",
    "items": [
      "Oqoltin","Boyovut","Guliston","Xovos","Mirzaobod","Sayxunobod","Sardoba",
      "Sirdaryo","Yangiyer","Shirin"
    ],
  },
  {
    "id": 12,
    "title": "Surxondaryo",
    "items": [
      "Angor","Boysun","Denov","Jarqoʻrgʻon","Qiziriq","Qumqoʻrgʻon","Muzrabot",
      "Oltinsoy","Sariosiyo","Sherobod","Shoʻrchi","Termiz","Uzun"
    ],
  },
  {
    "id": 13,
    "title": "Toshkent",
    "items": [
      "Bekobod","Boʻstonliq","Boʻka","Chinoz","Qibray","Ohangaron","Oqqoʻrgʻon",
      "Parkent","Piskent","Quyi Chirchiq","Oʻrta Chirchiq","Yangiyoʻl",
      "Yuqori Chirchiq","Zangiota"
    ],
  },
  {
    "id": 14,
    "title": "Toshkent shahri",
    "items": [
      "Bektemir","Chilonzor","Hamza","Mirobod","Mirzo Ulugʻbek","Sergeli","Shayxontohur",
      "Olmazor","Uchtepa","Yakkasaroy","Yunusobod","Yangihayot"
    ],
  },
]

class RegionViewSet(viewsets.ViewSet):
    """
    Regionlar bilan ishlash uchun ViewSet
    """
    
    def list(self, request):
        """Barcha region nomlarini qaytaradi"""
        return Response([r["title"] for r in regions])
    
    @action(detail=False, methods=['get'], url_path='(?P<region_name>[^/.]+)/districts')
    def get_region_items(self, request, region_name=None):
        """Region nomi orqali itemslarni qaytaradi"""
        for r in regions:
            if r["title"].lower() == region_name.lower():
                return Response(r["items"])
        return Response({"error": "Region topilmadi"}, status=status.HTTP_404_NOT_FOUND)