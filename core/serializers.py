from rest_framework import serializers
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class AboutSerializer(serializers.ModelSerializer):
    main_image = serializers.ImageField(required=False) 
    
    class Meta:
        model = About
        fields = '__all__'

class BlogSerializer(serializers.ModelSerializer):
    views = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = "__all__"
        read_only_fields = ("id", "slug", "created_date")

    def get_views(self, obj):
        return obj.hit_count.hits if hasattr(obj, "hit_count") else 0
        
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class SubcategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.title", read_only=True)

    class Meta:
        model = Subcategory
        fields = "__all__"
        read_only_fields = ("slug",)
        
class ApplicationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationImage
        fields = ["id", "application", "image"]
        read_only_fields = ["id"]


class ApplicationSerializer(serializers.ModelSerializer):
    images = ApplicationImageSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = ("slug",)

    def validate(self, data):
        category = data.get("category") or getattr(self.instance, "category", None)
        subcategory = data.get("subcategory") or getattr(self.instance, "subcategory", None)

        if subcategory and category and subcategory.category != category:
            raise serializers.ValidationError(
                {"subcategory": f"Tanlangan subcategory '{subcategory}' faqat '{subcategory.category}' "
                                f"categoriyasiga tegishli. Siz esa '{category}' categoriyasini tanladingiz."}
            )
        return data
    
class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email allaqachon ro‘yxatdan o‘tgan.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],  # username sifatida email ishlatyapmiz
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

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Email yoki parol noto‘g‘ri")

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
            }
        }