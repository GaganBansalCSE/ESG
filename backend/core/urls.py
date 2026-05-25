from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationViewSet, DataSourceViewSet, RawIngestionViewSet,
    NormalizedRowViewSet, ApprovalLogViewSet, DashboardView
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'data-sources', DataSourceViewSet, basename='data-source')
router.register(r'raw-ingestions', RawIngestionViewSet, basename='raw-ingestion')
router.register(r'rows', NormalizedRowViewSet, basename='normalized-row')
router.register(r'approval-logs', ApprovalLogViewSet, basename='approval-log')
router.register(r'dashboard', DashboardView, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
