"""
Django admin configuration for managing models through the admin interface.
"""

from django.contrib import admin

from .models import ChatMessage, ChatRoom, Collection, CollectionItem, Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin interface for Item model."""

    list_display = ["id", "name", "created_at", "updated_at"]
    search_fields = ["name", "description"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin interface for ChatRoom model."""

    list_display = [
        "id",
        "name",
        "room_type",
        "patient_name",
        "patient_language",
        "doctor_language",
        "has_rag",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "patient_name"]
    list_filter = ["room_type", "is_active", "patient_language", "doctor_language", "created_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "room_type", "is_active")}),
        ("Patient Information", {"fields": ("patient_name",)}),
        ("Language Settings", {"fields": ("patient_language", "doctor_language")}),
        ("RAG Configuration", {"fields": ("rag_collection",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "updated_at"]

    def has_rag(self, obj):
        """Show if room has RAG collection."""
        return obj.rag_collection is not None

    has_rag.boolean = True
    has_rag.short_description = "RAG Enabled"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin interface for ChatMessage model."""

    list_display = ["id", "room", "sender_type", "original_text_preview", "has_image", "has_audio", "created_at"]
    search_fields = ["original_text", "translated_text", "audio_transcription"]
    list_filter = ["sender_type", "has_image", "has_audio", "created_at", "room"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Message Information", {"fields": ("room", "sender_type")}),
        ("Original Content", {"fields": ("original_text", "original_language")}),
        ("Translation", {"fields": ("translated_text", "translated_language")}),
        ("Image Content", {"fields": ("has_image", "image_url", "image_description"), "classes": ("collapse",)}),
        (
            "Audio Content",
            {"fields": ("has_audio", "audio_file", "audio_duration", "audio_transcription"), "classes": ("collapse",)},
        ),
        ("Timestamp", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "audio_transcription"]

    def original_text_preview(self, obj):
        """Show preview of original text."""
        return obj.original_text[:50] + "..." if len(obj.original_text) > 50 else obj.original_text

    original_text_preview.short_description = "Original Text"


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """Admin interface for Collection model."""

    list_display = [
        "id",
        "name",
        "embedding_provider",
        "embedding_model",
        "embedding_dimensions",
        "items_count",
        "created_at",
    ]
    search_fields = ["name", "description"]
    list_filter = ["embedding_provider", "chunking_strategy", "created_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description")}),
        ("Embedding Configuration", {"fields": ("embedding_provider", "embedding_model", "embedding_dimensions")}),
        ("Completion Configuration", {"fields": ("completion_model",)}),
        (
            "Chunking Configuration",
            {"fields": ("chunking_strategy", "chunk_length", "chunk_overlap"), "classes": ("collapse",)},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "updated_at"]

    def items_count(self, obj):
        """Show number of items in collection."""
        return obj.items.count()

    items_count.short_description = "Documents"


@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    """Admin interface for CollectionItem model."""

    list_display = ["id", "name", "collection", "content_preview", "has_embedding", "created_at"]
    search_fields = ["name", "description", "content"]
    list_filter = ["collection", "created_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "collection")}),
        ("Content", {"fields": ("content",)}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
        ("Embedding", {"fields": ("embedding_info",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "updated_at", "embedding_info"]

    def content_preview(self, obj):
        """Show preview of content."""
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    content_preview.short_description = "Content Preview"

    def has_embedding(self, obj):
        """Show if item has embedding."""
        return obj.embedding is not None and len(obj.embedding) > 0

    has_embedding.boolean = True
    has_embedding.short_description = "Has Embedding"

    def embedding_info(self, obj):
        """Show embedding information."""
        if obj.embedding:
            return f"Vector with {len(obj.embedding)} dimensions"
        return "No embedding generated"

    embedding_info.short_description = "Embedding Info"
