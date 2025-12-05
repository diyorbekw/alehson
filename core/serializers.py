from rest_framework import serializers
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


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


class CategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class SubcategorySerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )

    class Meta:
        model = Subcategory
        fields = "__all__"
        read_only_fields = ("slug",)


class ApplicationImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    image_url = serializers.URLField(read_only=True)

    class Meta:
        model = ApplicationImage
        fields = ["id", "application", "image", "image_url"]
        read_only_fields = ["id", "image_url"]


class ApplicationSerializer(serializers.ModelSerializer):
    images = ApplicationImageSerializer(many=True, read_only=True)
    category_title = serializers.SerializerMethodField()
    subcategory_title = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "slug", "full_name", "phone_number", "birth_date",
            "passport_number", "region", "location", 
            "category", "subcategory",  # Bu hali ham foreign key ID sifatida qoladi
            "category_title", "subcategory_title",  # Yangi fieldlar
            "description", "status", "denied_reason", "images"
        ]
        read_only_fields = ("slug", "category_title", "subcategory_title")

    def get_category_title(self, obj):
        return obj.category.title if obj.category else None

    def get_subcategory_title(self, obj):
        return obj.subcategory.title if obj.subcategory else None

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