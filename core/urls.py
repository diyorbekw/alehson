from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GoogleAuthView, AboutAPIView, BannerViewSet, BlogViewSet,
    CategoryViewSet, SubcategoryViewSet, ApplicationViewSet,
    ApplicationImageViewSet, RegisterView, LoginView,
    TokenRefreshView, ProfileAPIView, TestAuthView,
    StatisticsAPIView, ContactUsViewSet,
    applications_by_category, applications_by_subcategory,
    filter_applications, index, dashboard, get_csrf_token
)

router = DefaultRouter()
router.register(r'banners', BannerViewSet, basename='banner')
router.register(r'blogs', BlogViewSet, basename='blog')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubcategoryViewSet, basename='subcategory')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'application-images', ApplicationImageViewSet, basename='applicationimage')
router.register(r'contact-us', ContactUsViewSet, basename='contactus')

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', dashboard, name='dashboard'),
    path('csrf/', get_csrf_token, name='csrf_token'),
    
    # Auth
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileAPIView.as_view(), name='profile'),
    path('auth/test/', TestAuthView.as_view(), name='test_auth'),
    
    # About
    path('about/', AboutAPIView.as_view(), name='about'),
    
    # Statistics
    path('statistics/', StatisticsAPIView.as_view(), name='statistics'),
    
    # Filter views
    path('applications/category/<int:category_id>/', applications_by_category, name='applications_by_category'),
    path('applications/subcategory/<int:subcategory_id>/', applications_by_subcategory, name='applications_by_subcategory'),
    path('applications/filter/', filter_applications, name='filter_applications'),
    
    # Router urls
    path('', include(router.urls)),
]