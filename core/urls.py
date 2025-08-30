from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import ensure_csrf_cookie

from .views import (
    GoogleAuthView,
    index,
    dashboard,
    get_csrf_token,
    AboutAPIView,
    BlogViewSet,
    CategoryViewSet,
    SubcategoryViewSet,
    ApplicationViewSet,
    ApplicationImageViewSet,
    RegisterView,
    LoginView,
    RegionViewSet
)

# API router faqat ViewSet lar uchun
router = DefaultRouter()
router.register(r"blogs", BlogViewSet, basename="blog")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"subcategories", SubcategoryViewSet, basename="subcategory")
router.register(r"applications", ApplicationViewSet, basename="application")
router.register(r"application-images", ApplicationImageViewSet, basename="application-image")
router.register(r"regions", RegionViewSet, basename="region")

urlpatterns = [
    # --- Frontend pages ---
    path("", index, name="index"),
    path("dashboard/", dashboard, name="dashboard"),
    path("get-csrf-token/", ensure_csrf_cookie(get_csrf_token), name="get_csrf_token"),

    # --- API (tartib bilan) ---
    path("api/auth/google/", GoogleAuthView.as_view(), name="google_auth"),
    path("api/about/", AboutAPIView.as_view(), name="about_api"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/", include(router.urls)),
]
