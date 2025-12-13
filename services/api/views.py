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

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .gemini_service import get_gemini_service
from .models import ChatMessage, ChatRoom, Collection, Item
from .rag_service import RAGService
from .serializers import ChatMessageSerializer, ChatRoomListSerializer, ChatRoomSerializer, ItemSerializer

logger = logging.getLogger(__name__)


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


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing chat rooms.
    """

    queryset = ChatRoom.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ChatRoomListSerializer
        return ChatRoomSerializer

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """
        Send a message in a chat room with automatic translation.

        POST /api/chat-rooms/{id}/send_message/
        Body: {
            "sender_type": "patient" or "doctor",
            "text": "message text",
            "image": "base64 image data (optional)",
            "audio": "base64 audio data (optional)"
        }
        """
        room = self.get_object()
        sender_type = request.data.get("sender_type")
        text = request.data.get("text")
        image_data = request.data.get("image")
        audio_data = request.data.get("audio")

        if not sender_type:
            return Response({"error": "sender_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not text and not audio_data:
            return Response({"error": "Either text or audio is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Determine languages
        if sender_type == "patient":
            original_lang = room.patient_language
            target_lang = room.doctor_language
        else:
            original_lang = room.doctor_language
            target_lang = room.patient_language

        # Get conversation history for context
        recent_messages = room.messages.order_by("-created_at")[:5]
        history = [
            {"sender_type": msg.sender_type, "text": msg.original_text} for msg in reversed(list(recent_messages))
        ]

        # Query RAG for relevant context if collection is configured
        rag_context = None
        if room.rag_collection:
            try:
                logger.info(f"RAG collection found: {room.rag_collection.name}")

                # Build context-aware query for RAG
                conversation_context = "\n".join([f"{h['sender_type']}: {h['text']}" for h in history])

                rag_query = f"""
Context: Medical conversation between patient and doctor.
Patient Language: {room.patient_language}
Doctor Language: {room.doctor_language}
Current Speaker: {sender_type}

Recent Conversation:
{conversation_context}

Current Message: {text}

Provide relevant cultural context, medical information, or language nuances that would help with accurate and culturally-sensitive translation.
"""

                # Query RAG collection
                rag_service = RAGService(room.rag_collection)
                rag_results = rag_service.query(rag_query, top_k=3)

                logger.info(f"RAG query returned {len(rag_results)} results")

                if rag_results:
                    # Combine top results into context
                    rag_context = "\n\n".join(
                        [f"Context from {r['name']}: {r['content'][:300]}" for r in rag_results[:2]]
                    )
                    logger.info(f"RAG context prepared: {len(rag_context)} chars")
                else:
                    logger.warning("RAG query returned no results")

            except Exception as e:
                logger.error(f"RAG context query failed: {e}", exc_info=True)

        # Translate message with RAG context
        try:
            gemini = get_gemini_service()
            translated_text = gemini.translate_with_context(
                text=text,
                source_lang=original_lang,
                target_lang=target_lang,
                conversation_history=history,
                sender_type=sender_type,
                rag_context=rag_context,
            )
        except Exception as e:
            return Response({"error": f"Translation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create message
        message = ChatMessage.objects.create(
            room=room,
            sender_type=sender_type,
            original_text=text,
            original_language=original_lang,
            translated_text=translated_text,
            translated_language=target_lang,
            has_image=bool(image_data),
            has_audio=bool(audio_data),
        )

        # Process audio if provided
        if audio_data:
            try:
                import base64

                from django.core.files.base import ContentFile

                # Decode base64 audio
                audio_bytes = base64.b64decode(audio_data)
                logger.info(f"Received audio: {len(audio_bytes)} bytes")

                # Check if audio is too small (likely empty) - reduced threshold for webm
                if len(audio_bytes) < 500:
                    message.delete()
                    logger.warning(f"Audio too small: {len(audio_bytes)} bytes")
                    return Response(
                        {"error": "Audio recording is too short or empty. Please record again."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Save audio file
                audio_file = ContentFile(audio_bytes, name=f"audio_{message.id}.webm")
                message.audio_file = audio_file
                message.save()

                # Transcribe audio with Gemini multimodal
                if not text or text == "[Voice Message]":
                    try:
                        gemini = get_gemini_service()
                        transcription_result = gemini.transcribe_audio(audio_bytes, source_lang=original_lang)

                        if transcription_result["success"]:
                            transcription = transcription_result["transcription"]
                            #  detected_lang = transcription_result["detected_language"]

                            # Check if transcription is empty
                            if not transcription or len(transcription.strip()) == 0:
                                message.delete()
                                return Response(
                                    {"error": "No speech detected in audio. Please speak clearly and try again."},
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                            # Update message with transcription
                            message.audio_transcription = transcription
                            message.original_text = transcription

                            # Re-translate the transcribed text with RAG context
                            translated_text = gemini.translate_with_context(
                                text=transcription,
                                source_lang=original_lang,
                                target_lang=target_lang,
                                conversation_history=history,
                                sender_type=sender_type,
                                rag_context=rag_context,
                            )
                            message.translated_text = translated_text
                            message.save()

                            logger.info(f"Audio transcribed and translated: {transcription[:50]}...")
                        else:
                            error_msg = transcription_result.get("error", "Unknown error")
                            message.delete()
                            logger.error(f"Audio transcription failed: {error_msg}")
                            return Response(
                                {"error": f"Audio transcription failed: {error_msg}"},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    except Exception as e:
                        message.delete()
                        logger.error(f"Audio transcription exception: {e}")
                        return Response(
                            {"error": f"Audio transcription error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

            except Exception as e:
                logger.error(f"Audio processing failed: {e}")
                message.delete()
                return Response(
                    {"error": f"Audio processing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Process image if provided
        if image_data:
            try:
                import base64

                image_bytes = base64.b64decode(image_data)
                result = gemini.analyze_image(image_bytes, target_lang)
                message.image_description = result.get("description")
                message.save()
            except Exception:
                # Image processing failed, but message is still saved
                pass

        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_patient_context(self, request, pk=None):
        """
        Add patient context document to the RAG collection.

        POST /api/chat-rooms/{id}/add_patient_context/
        Body: {
            "collection_id": 123,  # Required if room doesn't have collection
            "patient_name": "John Doe",
            "cultural_background": "...",
            "medical_history": "...",
            "language_notes": "..."
        }
        """
        room = self.get_object()

        # Get or set collection
        collection_id = request.data.get("collection_id")
        if collection_id:
            try:
                collection = Collection.objects.get(id=collection_id)
                room.rag_collection = collection
                room.save()
            except Collection.DoesNotExist:
                return Response(
                    {"error": f"Collection with id {collection_id} not found"}, status=status.HTTP_404_NOT_FOUND
                )
        elif not room.rag_collection:
            return Response(
                {"error": "No RAG collection configured. Please provide collection_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient_name = request.data.get("patient_name", room.patient_name or "Unknown Patient")
        cultural_background = request.data.get("cultural_background", "")
        medical_history = request.data.get("medical_history", "")
        language_notes = request.data.get("language_notes", "")

        # Build comprehensive patient profile document
        document_content = f"""
PATIENT PROFILE: {patient_name}

CULTURAL BACKGROUND:
{cultural_background}

MEDICAL HISTORY:
{medical_history}

LANGUAGE & COMMUNICATION NOTES:
{language_notes}

PRIMARY LANGUAGE: {room.patient_language}
DOCTOR LANGUAGE: {room.doctor_language}
CHAT ROOM: {room.name}
"""

        try:
            rag_service = RAGService(room.rag_collection)
            item = rag_service.add_document(
                name=f"Patient Profile: {patient_name}",
                content=document_content,
                description=f"Comprehensive profile for {patient_name} including cultural and medical context",
                metadata={
                    "type": "patient_profile",
                    "patient_name": patient_name,
                    "chat_room_id": room.id,
                    "languages": [room.patient_language, room.doctor_language],
                },
            )

            # Update room with patient name
            if not room.patient_name:
                room.patient_name = patient_name
                room.save()

            return Response(
                {"status": "success", "message": "Patient context added successfully", "document_id": item.id},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to add patient context: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def get_doctor_assistance(self, request, pk=None):
        """
        Get AI-powered assistance for doctors based on conversation and RAG context.

        GET /api/chat-rooms/{id}/get_doctor_assistance/

        Returns suggestions for:
        - Culturally-appropriate questions
        - Potential misunderstandings to clarify
        - Relevant medical information
        - Communication tips
        """
        room = self.get_object()

        if not room.rag_collection:
            return Response(
                {"status": "no_collection", "message": "No RAG collection configured", "suggestions": []},
                status=status.HTTP_200_OK,
            )

        # Get recent conversation
        recent_messages = room.messages.order_by("-created_at")[:10]
        conversation_context = "\n".join(
            [f"{msg.sender_type}: {msg.original_text}" for msg in reversed(list(recent_messages))]
        )

        # Build assistance query
        assistance_query = f"""
Based on this medical conversation, provide assistance to the doctor:

Patient Language: {room.patient_language}
Doctor Language: {room.doctor_language}

Recent Conversation:
{conversation_context}

Please suggest:
1. Important follow-up questions considering cultural context
2. Potential communication barriers or misunderstandings to clarify
3. Cultural sensitivities to be aware of
4. Relevant medical information from patient history

Format your response with clear sections.
"""

        try:
            rag_service = RAGService(room.rag_collection)
            result = rag_service.query_and_answer(assistance_query, top_k=5)

            if result["status"] == "success":
                return Response(
                    {
                        "status": "success",
                        "assistance": result["answer"],
                        "sources": result.get("sources", []),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "error", "message": result.get("message", "Failed to generate assistance")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing chat messages (read-only).
    Messages are created through ChatRoomViewSet.send_message action.
    """

    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        room_id = self.request.query_params.get("room_id")
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        return queryset


@api_view(["GET"])
def health_check(request):
    """
    Health check endpoint to verify the API is running.

    Returns:
        200 OK with a ping response
    """
    return Response({"status": "ok", "message": "pong"}, status=status.HTTP_200_OK)
