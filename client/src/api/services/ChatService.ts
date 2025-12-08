import ApiClient from '../ApiClient';

export interface ChatRoom {
  id: number;
  name: string;
  room_type: string;
  patient_language: string;
  doctor_language: string;
  patient_name?: string;
  rag_collection?: number;
  rag_collection_name?: string;
  has_rag?: boolean;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count?: number;
  last_message?: {
    text: string;
    sender: string;
    created_at: string;
  };
}

export interface ChatMessage {
  id: number;
  room: number;
  sender_type: 'patient' | 'doctor';
  original_text: string;
  original_language: string;
  translated_text: string;
  translated_language: string;
  has_image: boolean;
  image_url?: string;
  image_description?: string;
  has_audio: boolean;
  audio_url?: string;
  audio_duration?: number;
  audio_transcription?: string;
  created_at: string;
}

export interface SendMessageRequest {
  sender_type: 'patient' | 'doctor';
  text: string;
  image?: string;
  audio?: string; // base64 encoded audio
}

interface PaginatedResponse<T> {
  results: T[];
  count?: number;
  next?: string | null;
  previous?: string | null;
}

const ChatService = {
  // Get all chat rooms
  getChatRooms: async (): Promise<ChatRoom[]> => {
    const response = await ApiClient.get<PaginatedResponse<ChatRoom> | ChatRoom[]>('/chat-rooms/');
    // Handle paginated response from Django REST Framework
    if (response && typeof response === 'object' && 'results' in response) {
      return response.results;
    }
    // Handle direct array response
    return Array.isArray(response) ? response : [];
  },

  // Get a specific chat room with messages
  getChatRoom: async (id: number): Promise<ChatRoom> =>
    ApiClient.get<ChatRoom>(`/chat-rooms/${id}/`),

  // Create a new chat room
  createChatRoom: async (data: Partial<ChatRoom>): Promise<ChatRoom> =>
    ApiClient.post<ChatRoom>('/chat-rooms/', data),

  // Send a message in a chat room
  sendMessage: async (roomId: number, data: SendMessageRequest): Promise<ChatMessage> =>
    ApiClient.post<ChatMessage>(`/chat-rooms/${roomId}/send_message/`, data),

  // Get messages for a room
  getMessages: async (roomId: number): Promise<ChatMessage[]> => {
    const response = await ApiClient.get<PaginatedResponse<ChatMessage> | ChatMessage[]>(
      `/messages/?room_id=${roomId}`
    );
    // Handle paginated response from Django REST Framework
    if (response && typeof response === 'object' && 'results' in response) {
      return response.results;
    }
    // Handle direct array response
    return Array.isArray(response) ? response : [];
  },

  // Delete a chat room
  deleteChatRoom: async (id: number): Promise<void> => ApiClient.delete<void>(`/chat-rooms/${id}/`),

  // Convert audio blob to base64
  audioBlobToBase64: async (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        // Remove the data URL prefix (e.g., "data:audio/webm;base64,")
        const base64Data = base64.split(',')[1];
        resolve(base64Data);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  },

  // Add patient context to RAG collection
  addPatientContext: async (
    roomId: number,
    data: {
      patient_name: string;
      cultural_background: string;
      medical_history: string;
      language_notes: string;
    }
  ): Promise<any> => ApiClient.post(`/chat-rooms/${roomId}/add_patient_context/`, data),

  // Get doctor assistance from RAG
  getDoctorAssistance: async (roomId: number): Promise<any> =>
    ApiClient.get(`/chat-rooms/${roomId}/get_doctor_assistance/`),
};

export default ChatService;
