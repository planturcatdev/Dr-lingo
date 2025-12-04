"""
Database models for the API.

This file defines the data structure for your application.
Each model class represents a database table.

Example: Item model demonstrates common field types and patterns.
"""

from django.db import models


class Item(models.Model):
    """
    Sample Item model demonstrating database integration.

    This is a simple example to show the pattern for creating models.
    Extend this or create new models following the same pattern.

    Fields:
    - name: Short text field (max 200 characters)
    - description: Long text field (unlimited length)
    - created_at: Timestamp automatically set when item is created
    """

    name = models.CharField(max_length=200, help_text="Name of the item")

    description = models.TextField(
        blank=True,  # Optional field
        help_text="Detailed description of the item",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,  # Automatically set to now when created
        help_text="Timestamp when the item was created",
    )

    class Meta:
        ordering = ["-created_at"]  # Newest items first
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self):
        """String representation of the item (used in admin interface)"""
        return self.name
