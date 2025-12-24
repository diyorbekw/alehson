from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs


# ==================== AUTH SERIALIZERS ====================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
    
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
    password = serializers.CharField(write_only=True)
    
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


# ==================== MODEL SERIALIZERS ====================
class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = About
        fields = '__all__'


class BlogSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='category.title', read_only=True)
    
    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['slug', 'views', 'created_date', 'updated_date']


class BlogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['title', 'content', 'image', 'category', 'tags', 'author', 'status']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class SubcategorySerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True)
    
    class Meta:
        model = Subcategory
        fields = '__all__'
        read_only_fields = ['slug']


class ApplicationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationImage
        fields = ['id', 'image', 'created_date', 'application']
        read_only_fields = ['created_date']


class ApplicationSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True)
    subcategory_title = serializers.CharField(source='subcategory.title', read_only=True)
    images = ApplicationImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['slug', 'status', 'denied_reason', 'created_date', 'updated_date']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'passport_number', 'passport_photo',
            'passport_scan', 'region', 'district', 'address', 'birth_date',
            'nationality', 'education', 'marital_status', 'children_count',
            'job_title', 'work_experience', 'category', 'subcategory',
            'other_info'
        ]


class ApplicationCreateSerializerWithFiles(serializers.ModelSerializer):
    video = serializers.FileField(required=False, allow_null=True)
    document = serializers.FileField(required=False, allow_null=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'passport_number', 'passport_photo',
            'passport_scan', 'region', 'district', 'address', 'birth_date',
            'nationality', 'education', 'marital_status', 'children_count',
            'job_title', 'work_experience', 'category', 'subcategory',
            'video', 'document', 'images', 'other_info'
        ]
    
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        video = validated_data.pop('video', None)
        document = validated_data.pop('document', None)
        
        application = Application.objects.create(
            **validated_data,
            video=video,
            document=document
        )
        
        # Rasm qo'shish
        for image in images:
            ApplicationImage.objects.create(application=application, image=image)
        
        return application


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    video = serializers.FileField(required=False, allow_null=True)
    document = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'passport_number', 'passport_photo',
            'passport_scan', 'region', 'district', 'address', 'birth_date',
            'nationality', 'education', 'marital_status', 'children_count',
            'job_title', 'work_experience', 'category', 'subcategory',
            'video', 'document', 'other_info', 'status'
        ]


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ['user', 'created_date', 'updated_date']


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