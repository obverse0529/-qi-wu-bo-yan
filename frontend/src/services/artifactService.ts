import apiClient from './api';
import type {
  Artifact,
  ArtifactListResponse,
  ArtifactImage,
  CreateArtifactRequest,
} from '@/types';

export const artifactService = {
  // List artifacts with pagination and filters
  async list(params?: {
    page?: number;
    page_size?: number;
    category?: string;
    dynasty?: string;
    search?: string;
  }): Promise<ArtifactListResponse> {
    const { data } = await apiClient.get('/artifacts', { params });
    return data;
  },

  // Get single artifact
  async get(id: string): Promise<Artifact> {
    const { data } = await apiClient.get(`/artifacts/${id}`);
    return data;
  },

  // Create new artifact
  async create(artifact: CreateArtifactRequest): Promise<Artifact> {
    const { data } = await apiClient.post('/artifacts', artifact);
    return data;
  },

  // Update artifact
  async update(
    id: string,
    artifact: Partial<CreateArtifactRequest>
  ): Promise<Artifact> {
    const { data } = await apiClient.put(`/artifacts/${id}`, artifact);
    return data;
  },

  // Delete artifact
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/artifacts/${id}`);
  },

  // Get categories
  async getCategories(): Promise<Array<{ name: string; count: number }>> {
    const { data } = await apiClient.get('/artifacts/categories/list');
    return data;
  },

  // Get dynasties
  async getDynasties(): Promise<Array<{ name: string; count: number }>> {
    const { data } = await apiClient.get('/artifacts/dynasties/list');
    return data;
  },

  // Upload image
  async uploadImage(
    artifactId: string,
    file: File,
    viewType: string
  ): Promise<ArtifactImage> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('view_type', viewType);

    const { data } = await apiClient.post(`/images/${artifactId}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // List images
  async listImages(artifactId: string): Promise<ArtifactImage[]> {
    const { data } = await apiClient.get(`/images/${artifactId}/images`);
    return data;
  },

  // Delete image
  async deleteImage(artifactId: string, imageId: string): Promise<void> {
    await apiClient.delete(`/images/${artifactId}/images/${imageId}`);
  },

  // Get reconstruction tasks
  async getTasks(params?: {
    artifact_id?: string;
    status?: string;
    limit?: number;
  }): Promise<Array<{
    id: string;
    artifact: string;
    artifact_id: string;
    type: string;
    status: string;
    progress: number;
    error_message?: string;
    created_at: string;
  }>> {
    const { data } = await apiClient.get('/reconstruction/tasks', { params });
    return data;
  },

  // Get image count
  async getImageCount(): Promise<number> {
    const { data } = await apiClient.get('/images/count');
    return data.count;
  },
};
