import apiClient from './api';
import type { KGQueryResponse } from '@/types';

export interface KGRelatedArtifact {
  artifact_id: string;
  name: string;
  dynasty: string | null;
  category: string | null;
  relationship: string;
}

export interface KGSearchResult {
  id: string;
  name: string;
  type: string;
  dynasty: string | null;
  category: string | null;
  connections: number;
}

export interface KGStatistics {
  node_counts: Record<string, number>;
}

export const kgService = {
  // Query artifact graph
  async queryGraph(
    artifactId: string,
    depth: number = 2
  ): Promise<KGQueryResponse> {
    const { data } = await apiClient.get('/kg/query', {
      params: { artifact_id: artifactId, depth },
    });
    return data;
  },

  // Search related artifacts
  async searchRelated(
    artifactId: string,
    types?: string[],
    limit: number = 10
  ): Promise<KGRelatedArtifact[]> {
    const params: Record<string, any> = { limit };
    if (types && types.length > 0) {
      params.types = types.join(',');
    }
    const { data } = await apiClient.get(`/kg/related/${artifactId}`, { params });
    return data;
  },

  // Keyword search
  async search(keyword: string, limit: number = 20): Promise<KGSearchResult[]> {
    const { data } = await apiClient.get('/kg/search', {
      params: { keyword, limit },
    });
    return data;
  },

  // Get statistics
  async getStatistics(): Promise<KGStatistics> {
    const { data } = await apiClient.get('/kg/stats');
    return data;
  },

  // Initialize KG
  async init(): Promise<{ success: boolean }> {
    const { data } = await apiClient.post('/kg/init');
    return data;
  },

  // Connect KG service
  async connect(): Promise<{ success: boolean }> {
    const { data } = await apiClient.post('/kg/connect');
    return data;
  },

  // Delete artifact from graph
  async deleteArtifact(artifactId: string): Promise<{ success: boolean }> {
    const { data } = await apiClient.delete(`/kg/artifact/${artifactId}`);
    return data;
  },
};

export default kgService;
