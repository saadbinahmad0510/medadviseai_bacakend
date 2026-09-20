from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConsultationViewSet, HealthCheckView, RegisterView

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet, basename='consultation')

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]
