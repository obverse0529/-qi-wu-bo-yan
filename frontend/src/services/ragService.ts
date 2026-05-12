import apiClient from './api';

export interface RagDocument {
  id: string;
  artifact_id: string;
  artifact_name: string;
  content: string;
  source: string;
  source_type: string;
  score?: number;
}

export interface RagSearchResult {
  results: RagDocument[];
  count: number;
}

export interface RagStatistics {
  name: string;
  count: number;
  connected: boolean;
  status?: string;
}

export const ragService = {
  // Search documents
  async search(params: {
    query: string;
    top_k?: number;
    artifact_id?: string;
    artifact_name?: string;
  }): Promise<RagSearchResult> {
    const { data } = await apiClient.get('/rag/search', { params });
    return data;
  },

  // Get documents for artifact
  async getArtifactDocuments(artifactId: string): Promise<{
    documents: RagDocument[];
    count: number;
  }> {
    const { data } = await apiClient.get(`/rag/artifacts/${artifactId}/documents`);
    return data;
  },

  // Get collection statistics
  async getStatistics(): Promise<RagStatistics> {
    const { data } = await apiClient.get('/rag/statistics');
    return data;
  },

  // Delete documents for artifact
  async deleteArtifactDocuments(artifactId: string): Promise<{
    deleted: number;
    message: string;
  }> {
    const { data } = await apiClient.delete(`/rag/artifacts/${artifactId}/documents`);
    return data;
  },

  // Connect RAG service
  async connect(): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.post('/rag/connect');
    return data;
  },

  // Disconnect RAG service
  async disconnect(): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.post('/rag/disconnect');
    return data;
  },
};

export default ragService;
