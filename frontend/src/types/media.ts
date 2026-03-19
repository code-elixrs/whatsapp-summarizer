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

export interface ChatMessage {
  id: string;
  media_item_id: string;
  sender: string | null;
  message: string;
  message_timestamp: string | null;
  message_order: number;
  is_sent: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessagesResponse {
  messages: ChatMessage[];
  total: number;
}

export interface ChatMessageUpdate {
  sender?: string | null;
  message?: string;
  message_timestamp?: string | null;
  is_sent?: boolean;
}

export interface OCRStatus {
  status: "pending" | "ocr_processing" | "completed" | "failed" | "not_found";
  progress: number;
  item_id: string;
  error?: string;
  result?: Record<string, unknown>;
}

export interface StitchStatus {
  status: "pending" | "stitching" | "completed" | "failed" | "not_found";
  progress: number;
  item_id: string;
  error?: string;
  result?: Record<string, unknown>;
}

// Unified chat stream types
export interface ChatStreamMessage {
  type: "message";
  id: string;
  sender: string | null;
  message: string;
  message_timestamp: string | null;
  message_order: number;
  is_sent: boolean;
  source_item_id: string;
  source_group_id: string | null;
  sort_key: string;
}

export interface ChatStreamEvent {
  type: "event";
  event_type: string;
  item_id: string;
  title: string | null;
  file_name: string;
  mime_type: string;
  platform: string | null;
  duration_seconds: number | null;
  item_timestamp: string | null;
  file_url: string;
  transcript_summary: string | null;
  sort_key: string;
}

export type ChatStreamEntry = ChatStreamMessage | ChatStreamEvent;

export interface ChatStreamResponse {
  entries: ChatStreamEntry[];
  total_messages: number;
  total_events: number;
}

// Search types
export interface SearchResultItem {
  result_type: "chat_message" | "transcript" | "media_item";
  item_id: string;
  space_id: string;
  space_name: string;
  content_type: string;
  title: string | null;
  file_name: string;
  snippet: string;
  item_timestamp: string | null;
  platform: string | null;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  total: number;
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
