"""
Database models for the API.

Models define the structure of database tables and relationships.
Each model class represents a table, and each attribute represents a field.
"""

from django.db import models


class Item(models.Model):
    """
    Example model for demonstration purposes.

    Fields:
        name: The name of the item
        description: A detailed description
        created_at: Timestamp when created
        updated_at: Timestamp when last updated
    """

    name = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ChatRoom(models.Model):
    """
    Chat room for patient-doctor translation conversations.
    """

    ROOM_TYPES = [
        ("patient_doctor", "Patient-Doctor"),
        ("general", "General"),
    ]

    name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="patient_doctor")
    patient_language = models.CharField(max_length=50, default="en")
    doctor_language = models.CharField(max_length=50, default="en")
    rag_collection = models.ForeignKey(
        "Collection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_rooms",
        help_text="RAG collection for cultural and medical context",
    )
    patient_name = models.CharField(max_length=200, blank=True, help_text="Patient name for context")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.patient_language} <-> {self.doctor_language})"


class ChatMessage(models.Model):
    """
    Individual messages in a chat room with translation support.
    """

    SENDER_TYPES = [
        ("patient", "Patient"),
        ("doctor", "Doctor"),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    original_text = models.TextField()
    original_language = models.CharField(max_length=50)
    translated_text = models.TextField(blank=True, null=True)
    translated_language = models.CharField(max_length=50, blank=True, null=True)
    has_image = models.BooleanField(default=False)
    image_url = models.URLField(blank=True, null=True)
    image_description = models.TextField(blank=True, null=True)
    has_audio = models.BooleanField(default=False)
    audio_file = models.FileField(upload_to="chat_audio/", null=True, blank=True)
    audio_duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds")
    audio_transcription = models.TextField(blank=True, help_text="Transcribed text from audio")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def audio_url(self):
        """Return full URL for audio file."""
        if self.audio_file:
            return self.audio_file.url
        return None

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender_type} - {self.original_text[:50]}"


class Collection(models.Model):
    """RAG Collection for document embeddings and retrieval."""

    class EmbeddingProvider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        GEMINI = "gemini", "Google Gemini"

    class ChunkingStrategy(models.TextChoices):
        FIXED_LENGTH = "fixed-length", "Fixed Length"
        WINDOW = "window", "Window"
        NO_CHUNKING = "no-chunking", "No Chunking"

    name = models.CharField(max_length=191, unique=True)
    description = models.TextField()
    embedding_provider = models.CharField(
        max_length=100, choices=EmbeddingProvider.choices, default=EmbeddingProvider.GEMINI
    )
    embedding_model = models.CharField(max_length=100, default="text-embedding-004")
    embedding_dimensions = models.PositiveIntegerField(default=768)
    completion_model = models.CharField(max_length=100, default="gemini-2.0-flash-exp")
    chunking_strategy = models.CharField(
        max_length=100, choices=ChunkingStrategy.choices, default=ChunkingStrategy.FIXED_LENGTH
    )
    chunk_length = models.PositiveIntegerField(default=1000, null=True, blank=True)
    chunk_overlap = models.PositiveIntegerField(default=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class CollectionItem(models.Model):
    """Individual document/item in a RAG collection."""

    name = models.CharField(max_length=191)
    description = models.TextField(blank=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="items")
    content = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    embedding = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.collection.name}"
