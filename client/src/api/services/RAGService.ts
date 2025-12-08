import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export interface Collection {
  id: number;
  name: string;
  description: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  completion_model: string;
  chunking_strategy: string;
  chunk_length: number | null;
  chunk_overlap: number | null;
  created_at: string;
  updated_at: string;
  items_count: number;
}

export interface CollectionItem {
  id: number;
  name: string;
  description: string;
  collection: number;
  collection_name: string;
  content: string;
  metadata: any;
  created_at: string;
  updated_at: string;
}

export interface QueryResult {
  query: string;
  results: Array<{
    name: string;
    content: string;
    similarity: number;
    metadata: any;
  }>;
}

export interface RAGAnswer {
  status: string;
  answer: string;
  sources: Array<{
    name: string;
    similarity: number;
    content: string;
  }>;
}

class RAGService {
  async getCollections(): Promise<Collection[]> {
    const response = await axios.get(`${API_URL}/collections/`);
    return response.data.results || response.data;
  }

  async getCollection(id: number): Promise<Collection> {
    const response = await axios.get(`${API_URL}/collections/${id}/`);
    return response.data;
  }

  async createCollection(data: Partial<Collection>): Promise<Collection> {
    const response = await axios.post(`${API_URL}/collections/`, data);
    return response.data;
  }

  async addDocument(
    collectionId: number,
    data: { name: string; content: string; description?: string; metadata?: any }
  ): Promise<CollectionItem> {
    const response = await axios.post(`${API_URL}/collections/${collectionId}/add_document/`, data);
    return response.data;
  }

  async queryCollection(
    collectionId: number,
    query: string,
    topK: number = 5
  ): Promise<QueryResult> {
    const response = await axios.post(`${API_URL}/collections/${collectionId}/query/`, {
      query,
      top_k: topK,
    });
    return response.data;
  }

  async queryAndAnswer(collectionId: number, query: string, topK: number = 5): Promise<RAGAnswer> {
    const response = await axios.post(`${API_URL}/collections/${collectionId}/query_and_answer/`, {
      query,
      top_k: topK,
    });
    return response.data;
  }

  async getCollectionItems(collectionId?: number): Promise<CollectionItem[]> {
    const url = collectionId
      ? `${API_URL}/collection-items/?collection=${collectionId}`
      : `${API_URL}/collection-items/`;
    const response = await axios.get(url);
    return response.data.results || response.data;
  }
}

export default new RAGService();
