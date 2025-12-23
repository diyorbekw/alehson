from rest_framework import serializers
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# ---------------- Banner ----------------
class BannerSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Banner
        fields = ["id", "image", "image_url", "created_date", "is_active"]
        read_only_fields = ["id", "image_url", "created_date"]
        
    def get_list_of_images(self, obj):
        return [obj.image_url] if obj.image_url else []

class AboutSerializer(serializers.ModelSerializer):
    main_image = serializers.ImageField(required=False)
    main_image_url = serializers.URLField(read_only=True)

    class Meta:
        model = About
        fields = "__all__"


class BlogSerializer(serializers.ModelSerializer):
    views = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Blog
        fields = "__all__"
        read_only_fields = ("id", "slug", "created_date")

    def get_views(self, obj):
        return obj.hit_count.hits if hasattr(obj, "hit_count") else 0


# ---------------- CategorySerializer (faqat title list) ----------------
class CategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)
    # Faqat subcategory title'larini list sifatida qaytarish
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("subcategories",)

    def get_subcategories(self, obj):
        """Categoryga tegishli subcategorylarning faqat title'larini list sifatida qaytarish"""
        # values_list('title', flat=True) orqali faqat title'lar listini olamiz
        return list(Subcategory.objects.filter(categories=obj).values_list('title', flat=True))


# ---------------- SubcategorySerializer ----------------
class SubcategorySerializer(serializers.ModelSerializer):
    # categories ni faqat title'larini list sifatida qaytarish
    categories_titles = serializers.SerializerMethodField()
    
    class Meta:
        model = Subcategory
        fields = "__all__"
        read_only_fields = ("slug",)

    def get_categories_titles(self, obj):
        """Har bir subcategoryga tegishli categorylarning title'larini qaytarish"""
        return [category.title for category in obj.categories.all()]

# ===============================================
# CUSTOM FIELD FOR MULTIPART FORM DATA
# ===============================================
class MultiPartJSONField(serializers.JSONField):
    """JSON ma'lumotlarini multipart/form-data dan qabul qilish uchun"""
    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                import json
                return json.loads(data)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON string")
        return data


# ---------------- ApplicationImage ----------------
class ApplicationImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = ApplicationImage
        fields = ["id", "application", "image", "image_url"]
        read_only_fields = ["id", "image_url"]


# ===============================================
# APPLICATION SERIALIZER WITH MULTIPART SUPPORT
# ===============================================
class ApplicationSerializer(serializers.ModelSerializer):
    images = ApplicationImageSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=True
    )
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(),
        required=True
    )
    video = serializers.FileField(required=False, allow_null=True)
    video_url = serializers.URLField(read_only=True)
    document = serializers.FileField(required=False, allow_null=True)
    document_url = serializers.URLField(read_only=True)
    
    # Category va subcategory malumotlarini ID orqali qabul qilish
    category_id = serializers.IntegerField(write_only=True, required=False)
    subcategory_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Application
        fields = [
            "id", "slug", "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "category", "subcategory",
            "category_id", "subcategory_id",  # Write only fields
            "description", "video", "video_url", "document", "document_url",
            "status", "denied_reason", "images", "created_date"
        ]
        read_only_fields = ("slug", "video_url", "document_url", "created_date")

    def to_internal_value(self, data):
        # category_id va subcategory_id ni category va subcategoryga o'tkazish
        if 'category_id' in data:
            data['category'] = data.pop('category_id')
        if 'subcategory_id' in data:
            data['subcategory'] = data.pop('subcategory_id')
        return super().to_internal_value(data)

    def validate(self, data):
        category = data.get("category")
        subcategory = data.get("subcategory")

        if subcategory and category and category not in subcategory.categories.all():
            raise serializers.ValidationError(
                {"subcategory": f"Tanlangan subcategory '{subcategory}' faqat "
                 f"'{', '.join([c.title for c in subcategory.categories.all()])}' "
                 f"kategoriyasiga tegishli. Siz esa '{category}' kategoriyasini tanladingiz."}
            )
        return data
    
    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
# ===============================================
# APPLICATION CREATE SERIALIZER (For multipart form)
# ===============================================
class ApplicationCreateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=True
    )
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(),
        required=True
    )
    video = serializers.FileField(required=False, allow_null=True)
    document = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Application
        fields = [
            "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "category", "subcategory",
            "description", "video", "document"
        ]

    
# ===============================================
# APPLICATION UPDATE SERIALIZER (For multipart form)
# ===============================================
class ApplicationUpdateSerializer(serializers.ModelSerializer):
    video = serializers.FileField(required=False, allow_null=True)
    document = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = Application
        fields = [
            "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "description", "video", "document"
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ["id", "email", "profile"]
    
    def get_profile(self, obj):
        try:
            profile = obj.profile
            return ProfileSerializer(profile).data
        except Profile.DoesNotExist:
            return None


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Profile
        fields = ["id", "email", "first_name", "last_name", "birth_date"]
        read_only_fields = ["id", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "email", "password"]
        # Bu qatorni qo'shing:
        ref_name = "CoreRegisterSerializer"  # Har qanday noyob nom berishingiz mumkin

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email allaqachon ro'yxatdan o'tgan.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email allaqachon ro'yxatdan o'tgan.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Email yoki parol noto'g'ri")

        user = authenticate(username=user.username, password=password)
        if not user:
            raise serializers.ValidationError("Email yoki parol noto'g'ri")

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user_data
        }


class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSerializer() 
    
# ---------------- ContactUs ----------------
class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = ["id", "full_name", "email", "theme", "message", "created_date", "is_read"]
        read_only_fields = ["id", "created_date"]