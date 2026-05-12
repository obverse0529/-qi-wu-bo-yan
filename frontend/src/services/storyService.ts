import apiClient from './api';
import type { ArtifactStory } from '@/types';

export const storyService = {
  // Generate story
  async generate(
    artifactId: string,
    storyType: 'brief' | 'standard' | 'detailed' = 'detailed'
  ): Promise<ArtifactStory> {
    const { data } = await apiClient.post('/stories/generate', {
      artifact_id: artifactId,
      story_type: storyType,
    });
    return data;
  },

  // Get latest story for artifact
  async getLatestStory(artifactId: string): Promise<ArtifactStory> {
    const { data } = await apiClient.get(`/artifacts/${artifactId}/story`);
    return data;
  },

  // Get all stories for artifact
  async getArtifactStories(artifactId: string): Promise<ArtifactStory[]> {
    const { data } = await apiClient.get(`/artifacts/${artifactId}/stories`);
    return data;
  },

  // Load story model
  async loadModel(): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.post('/stories/model/load');
    return data;
  },

  // Unload story model
  async unloadModel(): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.post('/stories/model/unload');
    return data;
  },
};

export default storyService;
