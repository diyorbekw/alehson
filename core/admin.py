from django.contrib import admin
from django.utils.html import format_html
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage, Banner, ContactUs


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_preview', 'is_active', 'created_date')
    list_filter = ('is_active', 'created_date')
    search_fields = ('image_url',)
    readonly_fields = ('image_url', 'created_date', 'image_preview')
    list_editable = ('is_active',)
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image_url)
        return "No Image"
    image_preview.short_description = "Image"


@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'theme', 'is_read', 'created_date')
    list_filter = ('theme', 'is_read', 'created_date')
    search_fields = ('full_name', 'email', 'theme', 'message')
    readonly_fields = ('created_date',)
    list_editable = ('is_read',)
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} xabar o'qilgan deb belgilandi.")
    mark_as_read.short_description = "Tanlangan xabarlarni o'qilgan deb belgilash"


@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ('main_title', 'hero_title')
    
    def has_add_permission(self, request):
        # Faqat bitta About obyekti bo'lishi uchun
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'region', 'get_hit_count', 'created_date', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'region', 'description')
    list_filter = ('region', 'created_date')
    readonly_fields = ('image_url', 'created_date')

    def get_hit_count(self, obj):
        return obj.hit_count.hits if hasattr(obj, "hit_count") else 0
    get_hit_count.short_description = "Views"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'get_subcategories_count')
    search_fields = ('title',)
    filter_horizontal = ('subcategories',)
    readonly_fields = ('image_url', 'image_preview')
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image_url)
        return "No Image"
    image_preview.short_description = "Image"

    def get_subcategories_count(self, obj):
        return obj.subcategories.count()
    get_subcategories_count.short_description = "Subcategories"


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_categories', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)

    def get_categories(self, obj):
        return ", ".join([c.title for c in obj.categories.all()])
    get_categories.short_description = "Categories"
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "categories":
            kwargs["queryset"] = Category.objects.all()
            kwargs["widget"] = admin.widgets.FilteredSelectMultiple(
                db_field.verbose_name,
                db_field.name in self.filter_vertical
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'category', 'subcategory', 'status', 'region', 'created_date')
    list_filter = ('status', 'region', 'category', 'subcategory')
    search_fields = ('full_name', 'phone_number', 'passport_number')
    readonly_fields = ('slug', 'video_url', 'document_url', 'created_date')
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('full_name', 'phone_number', 'birth_date', 'passport_number')
        }),
        ('Manzil', {
            'fields': ('region', 'location')
        }),
        ('Kategoriya', {
            'fields': ('category', 'subcategory')
        }),
        ('Qo\'shimcha', {
            'fields': ('description', 'video', 'video_url', 'document', 'document_url')
        }),
        ('Status', {
            'fields': ('status', 'denied_reason', 'slug', 'created_date')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filter qilish uchun additional query parameters
        category_id = request.GET.get('category__id__exact')
        subcategory_id = request.GET.get('subcategory__id__exact')
        
        if category_id:
            qs = qs.filter(category_id=category_id)
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)
            
        return qs
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['categories'] = Category.objects.all()
        extra_context['subcategories'] = Subcategory.objects.all()
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ApplicationImage)
class ApplicationImageAdmin(admin.ModelAdmin):
    list_display = ('application', 'image_url_preview')
    readonly_fields = ('image_url', 'image_preview')
    
    def image_url_preview(self, obj):
        return obj.image_url[:50] + "..." if len(obj.image_url) > 50 else obj.image_url
    image_url_preview.short_description = "Image URL"
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 150px;" />', obj.image_url)
        return "No Image"
    image_preview.short_description = "Image"
