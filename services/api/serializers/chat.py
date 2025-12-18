from rest_framework import serializers

from api.models import ChatMessage, ChatRoom


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model with translation support."""

    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "room",
            "sender_type",
            "original_text",
            "original_language",
            "translated_text",
            "translated_language",
            "has_image",
            "image_url",
            "image_description",
            "has_audio",
            "audio_url",
            "audio_duration",
            "audio_transcription",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "translated_text",
            "translated_language",
            "image_description",
            "audio_url",
            "audio_transcription",
        ]

    def get_audio_url(self, obj):
        if obj.audio_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for ChatRoom model."""

    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    rag_collection_name = serializers.CharField(source="rag_collection.name", read_only=True)

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "name",
            "room_type",
            "patient_language",
            "doctor_language",
            "patient_name",
            "rag_collection",
            "rag_collection_name",
            "created_at",
            "updated_at",
            "is_active",
            "messages",
            "message_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatRoomListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing chat rooms (without messages)."""

    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    rag_collection_name = serializers.CharField(source="rag_collection.name", read_only=True)
    has_rag = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "name",
            "room_type",
            "patient_language",
            "doctor_language",
            "patient_name",
            "rag_collection",
            "rag_collection_name",
            "has_rag",
            "created_at",
            "updated_at",
            "is_active",
            "message_count",
            "last_message",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_has_rag(self, obj):
        return obj.rag_collection is not None

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                "text": last_msg.original_text[:100],
                "sender": last_msg.sender_type,
                "created_at": last_msg.created_at,
            }
        return None
