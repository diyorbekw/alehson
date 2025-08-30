from django.db import models
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.exceptions import ValidationError
from hitcount.models import HitCountMixin, HitCount
from django.contrib.contenttypes.fields import GenericRelation

class About(models.Model):
    main_title = models.CharField(max_length=255)
    main_image = models.ImageField(upload_to='about/')
    hero_title = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.main_title
    
    class Meta:
        verbose_name = 'About'
        verbose_name_plural = 'About'

class Blog(models.Model, HitCountMixin):
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=255)
    content = RichTextUploadingField()
    region = models.CharField(max_length=100)
    image = models.ImageField(upload_to="blogs/")
    created_date = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)

    hit_count_generic = GenericRelation(
        HitCount,
        object_id_field="object_pk",
        related_query_name="hit_count_generic_relation"
    )

    def save(self, *args, **kwargs): 
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Category(models.Model):
    image = models.ImageField(upload_to="categories/")
    title = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.title} → {self.title}"
    
    class Meta:
        verbose_name = 'Subcategory'
        verbose_name_plural = 'Subcategories'
        
class Application(models.Model):
    REGION_CHOICES = [
        ('Toshkent', 'Toshkent'),
        ('Samarqand', 'Samarqand'),
        ('Buxoro', 'Buxoro'),
        ('Farg\'ona', 'Farg\'ona'),
        ('Andijon', 'Andijon'),
        ('Namangan', 'Namangan'),
        ('Qashqadaryo', 'Qashqadaryo'),
        ('Surxondaryo', 'Surxondaryo'),
        ('Jizzax', 'Jizzax'),
        ('Sirdaryo', 'Sirdaryo'),
        ('Xorazm', 'Xorazm'),
        ('Navoiy', 'Navoiy'),
        ('Qoraqalpog\'iston', 'Qoraqalpog\'iston'),
    ]
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    birth_date = models.DateField()
    passport_number = models.CharField(max_length=50)
    region = models.CharField(max_length=50, choices=REGION_CHOICES)
    location = models.CharField(max_length=255)
    category = models.ForeignKey("Category", on_delete=models.CASCADE)
    subcategory = models.ForeignKey("Subcategory", on_delete=models.CASCADE)
    description = models.TextField()
    slug = models.SlugField(unique=True, blank=True)

    def clean(self):
        # category va subcategory mosligini tekshirish
        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError({
                "subcategory": f"Tanlangan subcategory '{self.subcategory}' "
                               f"faqat '{self.subcategory.category}' categoriyasiga tegishli. "
                               f"Siz esa '{self.category}' categoriyasini tanladingiz."
            })

    def save(self, *args, **kwargs):
        self.clean()  
        if not self.slug:
            base_slug = slugify(self.full_name)
            slug = base_slug
            counter = 1
            while Application.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
    
class ApplicationImage(models.Model):
    application = models.ForeignKey(
        Application,
        related_name="images",
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="applications/")
    
    def __str__(self):
        return f"Image for {self.application.full_name}"
    
    class Meta:
        verbose_name = 'Application Image'
        verbose_name_plural = 'Application Images'