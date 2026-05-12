// API Types for 启物博言

export interface Artifact {
  id: string;
  name: string;
  dynasty?: string;
  category?: string;
  dimensions?: {
    length: number;
    width: number;
    height: number;
    unit: string;
  };
  description?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ArtifactListResponse {
  items: Artifact[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ArtifactImage {
  id: string;
  artifact_id: string;
  view_type?: string;
  image_url?: string;
  thumbnail_url?: string;
  width?: number;
  height?: number;
  file_size?: number;
  created_at: string;
}

export interface ArtifactModel {
  id: string;
  artifact_id: string;
  model_url?: string;
  polygon_count?: number;
  has_texture: boolean;
  file_size?: number;
  status: string;
  created_at: string;
}

export interface ReconstructionTask {
  id: string;
  artifact_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  model_id?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface StoryContent {
  origin: string;
  craftsmanship: string;
  historical_context: string;
  cultural_significance: string;
  related_events: string[];
  similar_artifacts: string[];
}

export interface ArtifactStory {
  id: string;
  artifact_id: string;
  story_type: 'brief' | 'standard' | 'detailed';
  content: StoryContent;
  audio_url?: string;
  audio_script?: string;
  created_at: string;
}

// Alias for backward compatibility
export type StoryResponse = ArtifactStory;

export interface CreateArtifactRequest {
  name: string;
  dynasty?: string;
  category?: string;
  dimensions?: Record<string, unknown>;
  description?: string;
}

export interface UploadImageRequest {
  artifact_id: string;
  file: File;
  view_type: string;
}

export interface GenerateStoryRequest {
  artifact_id: string;
  story_type: 'brief' | 'standard' | 'detailed';
}

export interface KGNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface KGEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface KGQueryResponse {
  nodes: KGNode[];
  edges: KGEdge[];
}
