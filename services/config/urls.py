"""
URL configuration for hackathon scaffold project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Hackathon API",
        default_version="v1",
        description="API documentation for the hackathon project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@hackathon.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Django admin interface
    path("admin/", admin.site.urls),
    # Swagger/OpenAPI documentation
    path("api/docs/swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/docs/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("api/docs/schema/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    # API endpoints - all API routes are prefixed with /api/
    path("api/", include("api.urls")),
]
