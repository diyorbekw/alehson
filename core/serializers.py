from rest_framework import serializers
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# ===============================================
# BANNER
# ===============================================
class BannerSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Banner
        fields = ["id", "image", "image_url", "created_date", "is_active"]
        read_only_fields = ["id", "image_url", "created_date"]

# ===============================================
# ABOUT
# ===============================================
class AboutSerializer(serializers.ModelSerializer):
    main_image = serializers.ImageField(required=True)
    main_image_url = serializers.URLField(read_only=True)

    class Meta:
        model = About
        fields = "__all__"
        read_only_fields = ["main_image_url"]

# ===============================================
# BLOG
# ===============================================
class BlogSerializer(serializers.ModelSerializer):
    views = serializers.SerializerMethodField()
    image = serializers.ImageField(required=True)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Blog
        fields = "__all__"
        read_only_fields = ("id", "slug", "created_date", "views", "image_url")

    def get_views(self, obj):
        return obj.hit_count.hits if hasattr(obj, "hit_count") else 0

# ===============================================
# CATEGORY
# ===============================================
class CategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)
    image_url = serializers.URLField(read_only=True)
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("subcategories", "image_url")

    def get_subcategories(self, obj):
        return list(Subcategory.objects.filter(categories=obj).values_list('title', flat=True))

# ===============================================
# SUBCATEGORY
# ===============================================
class SubcategorySerializer(serializers.ModelSerializer):
    categories_titles = serializers.SerializerMethodField()
    
    class Meta:
        model = Subcategory
        fields = "__all__"
        read_only_fields = ("slug",)

    def get_categories_titles(self, obj):
        return [category.title for category in obj.categories.all()]

# ===============================================
# APPLICATION IMAGE
# ===============================================
class ApplicationImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = ApplicationImage
        fields = ["id", "application", "image", "image_url"]
        read_only_fields = ["id", "image_url"]

# ===============================================
# APPLICATION CREATE SERIALIZER (MULTIPART UCHUN)
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
    video = serializers.FileField(required=False, allow_null=True, allow_empty_file=True)
    document = serializers.FileField(required=False, allow_null=True, allow_empty_file=True)
    
    # Bir nechta rasm yuklash uchun
    images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        required=False,
        write_only=True,
        allow_empty=True
    )

    class Meta:
        model = Application
        fields = [
            "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "category", "subcategory", "description", 
            "video", "document", "images"
        ]

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
        # Rasmlarni alohida olish
        images_data = validated_data.pop('images', [])
        
        # Video va hujjatlar
        video = validated_data.pop('video', None)
        document = validated_data.pop('document', None)
        
        # Ariza yaratish
        application = Application.objects.create(
            video=video,
            document=document,
            **validated_data
        )
        
        # Rasmlarni yaratish
        for image in images_data:
            ApplicationImage.objects.create(
                application=application,
                image=image
            )
            
        return application

# ===============================================
# APPLICATION SERIALIZER
# ===============================================
class ApplicationSerializer(serializers.ModelSerializer):
    images = ApplicationImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)
    video = serializers.FileField(required=False, allow_null=True, allow_empty_file=True)
    video_url = serializers.URLField(read_only=True)
    document = serializers.FileField(required=False, allow_null=True, allow_empty_file=True)
    document_url = serializers.URLField(read_only=True)
    
    # Write-only fields for creating/updating
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(),
        source='subcategory',
        write_only=True,
        required=False
    )

    class Meta:
        model = Application
        fields = [
            "id", "slug", "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "category", "subcategory", "category_id", "subcategory_id",
            "description", "video", "video_url", "document", "document_url",
            "status", "denied_reason", "images", "created_date"
        ]
        read_only_fields = ("slug", "video_url", "document_url", "created_date", 
                          "status", "denied_reason")

# ===============================================
# USER & PROFILE
# ===============================================
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
        ref_name = "CoreRegisterSerializer"

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

# ===============================================
# CONTACT US
# ===============================================
class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = ["id", "full_name", "email", "theme", "message", "created_date", "is_read"]
        read_only_fields = ["id", "created_date"]