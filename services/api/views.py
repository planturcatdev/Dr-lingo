"""
API views (endpoints) for handling HTTP requests.

ViewSets provide the logic for handling CRUD operations:
- List all items (GET /api/items/)
- Create new item (POST /api/items/)
- Retrieve single item (GET /api/items/:id/)
- Update item (PUT /api/items/:id/)
- Delete item (DELETE /api/items/:id/)

Example: ItemViewSet demonstrates the standard pattern for API endpoints.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Item
from .serializers import ItemSerializer


class ItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Item CRUD operations.

    ModelViewSet automatically provides:
    - list(): GET /api/items/ - List all items
    - create(): POST /api/items/ - Create a new item
    - retrieve(): GET /api/items/:id/ - Get a specific item
    - update(): PUT /api/items/:id/ - Update an item
    - partial_update(): PATCH /api/items/:id/ - Partially update an item
    - destroy(): DELETE /api/items/:id/ - Delete an item

    To customize behavior, override these methods.
    """

    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    # Example: Override create to add custom logic
    # def create(self, request, *args, **kwargs):
    #     """Custom create logic"""
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def health_check(request):
    """
    Health check endpoint to verify the API is running.

    Returns:
        200 OK with a ping response
    """
    return Response({"status": "ok", "message": "pong"}, status=status.HTTP_200_OK)
