export type ContentType = "call_recording" | "chat_screenshot" | "status_update" | "other_media";
export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";
export type TimestampSource = "auto_detected" | "user_provided" | "file_metadata";

export interface MediaItem {
  id: string;
  space_id: string;
  content_type: ContentType;
  title: string | null;
  notes: string | null;
  file_name: string;
  file_size: number;
  mime_type: string;
  item_timestamp: string | null;
  timestamp_source: TimestampSource;
  processing_status: ProcessingStatus;
  group_id: string | null;
  group_order: number | null;
  stitched_path: string | null;
  platform: string | null;
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
  file_url: string;
}

export interface MediaItemListResponse {
  items: MediaItem[];
  total: number;
}

export interface MediaItemUpdate {
  title?: string | null;
  notes?: string | null;
  content_type?: ContentType;
  item_timestamp?: string | null;
  timestamp_source?: TimestampSource;
  platform?: string | null;
}

export interface TranscriptSegment {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
  segment_index: number;
}

export interface Transcript {
  id: string;
  media_item_id: string;
  full_text: string;
  language: string | null;
  segments: TranscriptSegment[];
  created_at: string;
}

export interface TranscriptionStatus {
  status: "pending" | "transcribing" | "completed" | "failed" | "not_found";
  progress: number;
  item_id: string;
  segments_done?: number;
  error?: string;
  result?: Record<string, unknown>;
}

export interface UploadingFile {
  id: string;
  file: File;
  contentType: ContentType;
  timestamp: string;
  status: "uploading" | "done" | "error";
  progress: number;
  error?: string;
}
