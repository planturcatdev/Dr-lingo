"""
URL routing for API endpoints.

This file maps URL patterns to views (endpoints).
The router automatically creates URL patterns for ViewSets.

Example: Items endpoint is available at /api/items/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ItemViewSet, health_check

# Create a router and register viewsets
# The router automatically generates URL patterns for CRUD operations
router = DefaultRouter()

# Register the Item viewset
# This creates the following URLs:
# - GET    /api/items/     -> List all items
# - POST   /api/items/     -> Create new item
# - GET    /api/items/:id/ -> Get specific item
# - PUT    /api/items/:id/ -> Update item
# - PATCH  /api/items/:id/ -> Partial update
# - DELETE /api/items/:id/ -> Delete item
router.register(r"items", ItemViewSet, basename="item")

# To add more endpoints, register additional viewsets:
# router.register(r'users', UserViewSet, basename='user')
# router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    # Include all router-generated URLs
    path("", include(router.urls)),
    # Health check endpoint
    path("health/", health_check, name="health-check"),
]
