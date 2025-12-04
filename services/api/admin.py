"""
Django admin configuration.

Register your models here to make them accessible in the Django admin interface.
The admin interface provides a web-based UI for managing your data.

Access the admin at: http://localhost:8000/admin/
"""

from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Item model.

    Customize the admin interface by setting:
    - list_display: Fields to show in the list view
    - list_filter: Add filters in the sidebar
    - search_fields: Enable search functionality
    - readonly_fields: Fields that cannot be edited
    """

    # Fields to display in the list view
    list_display = ["id", "name", "description", "created_at"]

    # Add filters in the sidebar
    list_filter = ["created_at"]

    # Enable search by name and description
    search_fields = ["name", "description"]

    # Make created_at read-only (it's auto-generated)
    readonly_fields = ["created_at"]

    # Order by newest first
    ordering = ["-created_at"]


# Alternative simple registration (without customization):
# admin.site.register(Item)

# To register additional models:
# @admin.register(YourModel)
# class YourModelAdmin(admin.ModelAdmin):
#     list_display = ['field1', 'field2']
