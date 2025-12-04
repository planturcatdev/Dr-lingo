"""
Serializers for converting between Python objects and JSON.

Serializers handle the transformation of complex data types (like Django models)
into JSON format that can be sent to the client, and vice versa.

Example: ItemSerializer demonstrates the basic pattern for model serialization.
"""

from rest_framework import serializers

from .models import Item


class ItemSerializer(serializers.ModelSerializer):
    """
    Serializer for the Item model.

    This automatically creates serializer fields for all model fields.
    The serializer handles:
    - Converting Item objects to JSON (for API responses)
    - Converting JSON to Item objects (for API requests)
    - Validating incoming data

    To add custom fields or validation, extend this class.
    """

    class Meta:
        model = Item
        fields = "__all__"  # Include all fields from the model
        # Alternative: fields = ['id', 'name', 'description', 'created_at']

        # Make created_at read-only (automatically set by database)
        read_only_fields = ["created_at"]


# Example of a custom serializer with additional fields:
# class ItemDetailSerializer(serializers.ModelSerializer):
#     """Extended serializer with computed fields"""
#
#     # Add a computed field
#     name_length = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Item
#         fields = ['id', 'name', 'description', 'created_at', 'name_length']
#         read_only_fields = ['created_at']
#
#     def get_name_length(self, obj):
#         """Compute the length of the name"""
#         return len(obj.name)
