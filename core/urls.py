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
    ProfileAPIView,
    TokenRefreshView,
    TestAuthView,
    StatisticsAPIView
)

# API router faqat ViewSet lar uchun
router = DefaultRouter()
router.register(r"blogs", BlogViewSet, basename="blog")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"subcategories", SubcategoryViewSet, basename="subcategory")
router.register(r"applications", ApplicationViewSet, basename="application")
router.register(r"application-images", ApplicationImageViewSet, basename="application-image")

urlpatterns = [
    # --- Frontend pages ---
    path("", index, name="index"),
    path("dashboard/", dashboard, name="dashboard"),
    path("get-csrf-token/", ensure_csrf_cookie(get_csrf_token), name="get_csrf_token"),

    # --- API Endpoints ---
    # "api/" prefiksi OLIB TASHLANDI (chunki asosiy urls.py da bor)
    path("auth/google/", GoogleAuthView.as_view(), name="google_auth"),
    path("about/", AboutAPIView.as_view(), name="about_api"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/test/", TestAuthView.as_view(), name="test_auth"),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path("statistics/", StatisticsAPIView.as_view(), name="statistics"),
    path("", include(router.urls)),  # Router endpoints: /blogs/, /categories/, etc.
]