from django.contrib import admin
from .models import About, Blog, Category, Subcategory, Application, ApplicationImage

# Register your models here.
@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ('main_title', 'hero_title', 'description')
    
@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'region', 'get_hit_count', 'created_date', 'slug')
    prepopulated_fields = {'slug': ('title',)}

    def get_hit_count(self, obj):
        return obj.hit_count.hits
    get_hit_count.short_description = "Views"
    
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title',)
    filter_horizontal = ('subcategories',)  # admin interfeysida ko‘proq qulay bo‘ladi
    

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_categories', 'slug')
    prepopulated_fields = {'slug': ('title',)}

    def get_categories(self, obj):
        return ", ".join([c.title for c in obj.categories.all()])
    get_categories.short_description = "Categories"
    
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'birth_date')
        
@admin.register(ApplicationImage)
class ApplicationImageAdmin(admin.ModelAdmin):
    list_display = ('application', 'image')