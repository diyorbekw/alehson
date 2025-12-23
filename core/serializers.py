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


# ---------------- ApplicationImage ----------------
class ApplicationImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = ApplicationImage
        fields = ["id", "application", "image", "image_url"]
        read_only_fields = ["id", "image_url"]


# ---------------- Application ----------------
class ApplicationSerializer(serializers.ModelSerializer):
    images = ApplicationImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)
    video = serializers.FileField(required=False, allow_null=True)
    video_url = serializers.URLField(read_only=True)
    document = serializers.FileField(required=False, allow_null=True)
    document_url = serializers.URLField(read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "slug", "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "category", "subcategory",
            "description", "video", "video_url", "document", "document_url",
            "status", "denied_reason", "images", "created_date"
        ]
        read_only_fields = ("slug", "category", "subcategory", "video_url", "document_url", "created_date")

    def get_category(self, obj):
        return obj.category

    def get_subcategory(self, obj):
        return obj.subcategory

    def validate(self, data):
        category = data.get("category") or getattr(self.instance, "category", None)
        subcategory = data.get("subcategory") or getattr(self.instance, "subcategory", None)

        if subcategory and category and category not in subcategory.categories.all():
            raise serializers.ValidationError(
                {"subcategory": f"Tanlangan subcategory '{subcategory}' faqat "
                 f"'{', '.join([c.title for c in subcategory.categories.all()])}' "
                 f"kategoriyasiga tegishli. Siz esa '{category}' kategoriyasini tanladingiz."}
            )
        return data
    
    def create(self, validated_data):
        # Remove image field if present (it will be handled in save method)
        validated_data.pop('image', None)
        return super().create(validated_data)


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