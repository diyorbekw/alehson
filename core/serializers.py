from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Profile, Banner, ContactUs


# ==================== AUTH SERIALIZERS ====================
class CustomRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
        ref_name = 'CoreCustomRegisterSerializer'
    
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
        ref_name = 'CoreUserSerializer'


# ==================== MODEL SERIALIZERS ====================
class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = About
        fields = '__all__'
        ref_name = 'CoreAboutSerializer'


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = '__all__'
        ref_name = 'CoreBlogSerializer'
        read_only_fields = ['slug', 'created_date']


class BlogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['title', 'description', 'content', 'region', 'image']
        ref_name = 'CoreBlogCreateSerializer'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        ref_name = 'CoreCategorySerializer'


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = '__all__'
        ref_name = 'CoreSubcategorySerializer'
        read_only_fields = ['slug']


class ApplicationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationImage
        fields = ['id', 'image', 'image_url', 'created_date', 'application']
        read_only_fields = ['created_date']
        ref_name = 'CoreApplicationImageSerializer'
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
        ref_name = 'CoreApplicationSerializer'
        read_only_fields = ['slug', 'status', 'denied_reason', 'created_date']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        default=[],
        write_only=True,
        help_text="Rasm fayllari listi (faqat .jpg, .jpeg, .png, .gif)"
    )

    
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'birth_date', 'passport_number',
            'region', 'location', 'category', 'subcategory', 'description',
            'video', 'document', 'images'
        ]
        read_only_fields = ['slug', 'status', 'denied_reason', 'created_date']
        ref_name = 'CoreApplicationCreateSerializer'
    
    def validate(self, data):
        category = data.get('category')
        subcategory = data.get('subcategory')
        
        if category and subcategory:
            if subcategory not in category.subcategories.all():
                raise serializers.ValidationError({
                    "subcategory": f"Tanlangan subcategory '{subcategory.title}' "
                                   f"'{category.title}' kategoriyasiga tegishli emas."
                })
        
        # Rasm fayllarini tekshirish
        images = data.get('images', [])
        for image in images:
            if hasattr(image, 'content_type'):
                content_type = image.content_type
                if not content_type.startswith('image/'):
                    raise serializers.ValidationError({
                        "images": f"Faqat rasm fayllari yuklanishi mumkin. Siz yuborgan: {content_type}"
                    })
        
        return data
    
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        
        # Application yaratish
        application = Application.objects.create(**validated_data)
        
        # Rasm fayllarini imgbb ga yuklash va saqlash
        for image_file in images:
            if image_file:
                ApplicationImage.objects.create(
                    application=application,
                    image=image_file  # save() methodi imgbb ga yuklaydi
                )
        
        return application


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    video_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    document_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Application
        fields = [
            'full_name', 'phone_number', 'birth_date', 'passport_number',
            'region', 'location', 'category', 'subcategory', 'description',
            'video_url', 'document_url', 'status'
        ]
        read_only_fields = ['slug', 'denied_reason', 'created_date']
        ref_name = 'CoreApplicationUpdateSerializer'
    
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
        ref_name = 'CoreProfileSerializer'
        read_only_fields = ['user']


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'
        ref_name = 'CoreBannerSerializer'
        read_only_fields = ['created_date']


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = '__all__'
        ref_name = 'CoreContactUsSerializer'
        read_only_fields = ['is_read', 'created_date']