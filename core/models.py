import requests
import base64
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from ckeditor_uploader.fields import RichTextUploadingField
from hitcount.models import HitCountMixin, HitCount
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth.models import User

CONTACT_THEME_CHOICES = [
    ('Ehson haqida', 'Ehson haqida'),
    ('Hamkorlik', 'Hamkorlik'),
    ('Texnik masala', 'Texnik masala'),
    ('Boshqa', 'Boshqa'),
]

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

IMGBB_API_KEY = "be90fbfa79386858ac1e2259531ab55e"


def upload_to_imgbb(image_field):
    """Rasmni imgbb ga yuklab, URL qaytaradi"""
    image_file = image_field.file
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(image_file.read()),
    }
    res = requests.post(url, payload)
    res.raise_for_status()
    data = res.json()
    return data["data"]["url"]



# ---------------- Profile ----------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


# ---------------- Banner ----------------
class Banner(models.Model):
    image = models.ImageField(upload_to="temp/")
    image_url = models.URLField(max_length=500, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.image and not self.image_url:
            try:
                self.image_url = upload_to_imgbb(self.image)
                self.image.delete(save=False)
            except ValidationError as e:
                raise e
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Banner {self.id} ({'Active' if self.is_active else 'Inactive'})"
    
    class Meta:
        ordering = ['-created_date']


# ---------------- About ----------------
class About(models.Model):
    main_title = models.CharField(max_length=255)
    main_image = models.ImageField(upload_to="temp/")
    main_image_url = models.URLField(max_length=500, blank=True)
    hero_title = models.CharField(max_length=255)
    description = models.TextField()

    def save(self, *args, **kwargs):
        if self.main_image and not self.main_image_url:
            try:
                self.main_image_url = upload_to_imgbb(self.main_image)
                self.main_image.delete(save=False)
            except ValidationError as e:
                raise e
        super().save(*args, **kwargs)

    def __str__(self):
        return self.main_title
    
    class Meta:
        verbose_name = "About"
        verbose_name_plural = "About"


# ---------------- ContactUs ----------------
class ContactUs(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    theme = models.CharField(max_length=50, choices=CONTACT_THEME_CHOICES)
    message = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.theme}"
    
    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ['-created_date']


# ---------------- Blog ----------------
class Blog(models.Model, HitCountMixin):
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=255)
    content = RichTextUploadingField()
    region = models.CharField(max_length=100, choices=REGION_CHOICES)
    image = models.ImageField(upload_to="temp/")
    image_url = models.URLField(max_length=500, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)

    hit_count_generic = GenericRelation(
        HitCount,
        object_id_field="object_pk",
        related_query_name="hit_count_generic_relation"
    )

    def save(self, *args, **kwargs):
        if self.image and not self.image_url:
            try:
                self.image_url = upload_to_imgbb(self.image)
                self.image.delete(save=False)
            except ValidationError as e:
                raise e
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_date']


# ---------------- Category ----------------
class Category(models.Model):
    image = models.ImageField(upload_to="temp/")
    image_url = models.URLField(max_length=500, blank=True)
    title = models.CharField(max_length=100, unique=True)
    subcategories = models.ManyToManyField(
        "Subcategory",
        related_name="categories",
        blank=True
    )

    def save(self, *args, **kwargs):
        if self.image and not self.image_url:
            try:
                self.image_url = upload_to_imgbb(self.image)
                self.image.delete(save=False)
            except ValidationError as e:
                raise e
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


# ---------------- Subcategory ----------------
class Subcategory(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        categories = ", ".join([c.title for c in self.categories.all()])
        return f"{self.title} ({categories})"
    
    class Meta:
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"


# ---------------- Application ----------------
class Application(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("denied", "Denied"),
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
    
    video = models.FileField(upload_to="temp/", blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True)
    document = models.FileField(upload_to="temp/", blank=True, null=True)
    document_url = models.URLField(max_length=500, blank=True)
    
    slug = models.SlugField(unique=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    denied_reason = models.TextField(blank=True, null=True)

    def clean(self):
        if self.subcategory and self.category not in self.subcategory.categories.all():
            raise ValidationError({
                "subcategory": f"Tanlangan subcategory '{self.subcategory}' "
                               f"'{self.category}' kategoriyasiga tegishli emas."
            })
        if self.status == "denied" and not self.denied_reason:
            raise ValidationError({"denied_reason": "Sabab kiritilishi kerak denied uchun."})

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
    
    class Meta:
        ordering = ['-created_date']


# ---------------- Application Image ----------------
class ApplicationImage(models.Model):
    application = models.ForeignKey(
        Application,
        related_name="images",
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="temp/")
    image_url = models.URLField(max_length=500, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.image and not self.image_url:
            try:
                self.image_url = upload_to_imgbb(self.image)
                self.image.delete(save=False)
            except ValidationError as e:
                raise e
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.application.full_name}"
    
    class Meta:
        verbose_name = "Application Image"
        verbose_name_plural = "Application Images"