from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs


# ==================== AUTH SERIALIZERS ====================
class CustomRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'email': {'required': True},
            'password': {'required': True}
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email allaqachon ro'yxatdan o'tgan")
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                user = authenticate(username=user.username, password=password)
                
                if not user:
                    raise serializers.ValidationError("Noto'g'ri email yoki parol")
                
                refresh = RefreshToken.for_user(user)
                
                return {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    }
                }
            except User.DoesNotExist:
                raise serializers.ValidationError("Foydalanuvchi topilmadi")
        else:
            raise serializers.ValidationError("Email va parolni kiriting")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


# ==================== MODEL SERIALIZERS ====================
class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = About
        fields = '__all__'
        read_only_fields = ['created_date', 'updated_date']


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['slug', 'created_date']


class BlogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['title', 'description', 'content', 'region', 'image']
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': True},
            'content': {'required': True}
        }


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ['created_date']


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = '__all__'
        read_only_fields = ['slug', 'created_date']


class ApplicationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationImage
        fields = ['id', 'image', 'image_url', 'created_date', 'application']
        read_only_fields = ['created_date', 'application']
        extra_kwargs = {
            'image': {'required': False},
            'image_url': {'required': False}
        }
    
    def validate(self, data):
        if not data.get('image') and not data.get('image_url'):
            raise serializers.ValidationError(
                "Iltimos, rasm fayli yoki rasm URL'ini kiriting"
            )
        return data


class ApplicationSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True)
    subcategory_title = serializers.CharField(source='subcategory.title', read_only=True)
    images = ApplicationImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['slug', 'status', 'denied_reason', 'created_date']


# ==================== APPLICATION CREATE SERIALIZER ====================
class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'birth_date', 'passport_number',
            'region', 'location', 'category', 'subcategory', 'description',
        ]
        extra_kwargs = {
            'full_name': {'required': True},
            'phone_number': {'required': True},
            'birth_date': {'required': True},
            'passport_number': {'required': True},
            'region': {'required': True},
            'category': {'required': True},
            'subcategory': {'required': True}
        }


class ApplicationCreateWithFilesSerializer(serializers.ModelSerializer):
    video = serializers.FileField(required=False, allow_null=True)
    document = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'birth_date', 'passport_number',
            'region', 'district', 'location', 'category', 'subcategory', 'description',
            'video', 'document'
        ]
        extra_kwargs = {
            'full_name': {'required': True},
            'phone_number': {'required': True},
            'birth_date': {'required': True},
            'passport_number': {'required': True},
            'region': {'required': True},
            'district': {'required': True},
            'category': {'required': True},
            'subcategory': {'required': True}
        }


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'birth_date', 'passport_number',
            'region', 'district', 'location', 'category', 'subcategory', 'description',
            'status'
        ]
        read_only_fields = ['slug', 'denied_reason', 'created_date']
        extra_kwargs = {
            'status': {'required': False}
        }
    
    def validate(self, data):
        category = data.get('category')
        subcategory = data.get('subcategory')
        
        if category and subcategory:
            if subcategory not in category.subcategories.all():
                raise serializers.ValidationError({
                    "subcategory": f"Tanlangan subcategory '{subcategory.title}' "
                                   f"'{category.title}' kategoriyasiga tegishli emas."
                })
        
        return data


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ['user', 'created_date']


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'
        read_only_fields = ['created_date']


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = '__all__'
        read_only_fields = ['is_read', 'created_date']
        extra_kwargs = {
            'full_name': {'required': True},
            'email': {'required': True},
            'theme': {'required': True},
            'message': {'required': True}
        }