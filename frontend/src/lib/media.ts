import type { ContentType, MediaItem, MediaItemListResponse, MediaItemUpdate, Transcript, ChatMessagesResponse, ChatMessageUpdate, ChatMessage } from "../types/media";
import { apiFetch } from "./api";

export async function uploadFile(
  spaceId: string,
  file: File,
  contentType: ContentType,
  timestamp?: string,
  onProgress?: (progress: number) => void,
  whisperModel?: string,
  groupId?: string,
  groupOrder?: number,
): Promise<MediaItem> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("content_type", contentType);
  if (timestamp) {
    formData.append("item_timestamp", timestamp);
  }
  if (whisperModel) {
    formData.append("whisper_model", whisperModel);
  }
  if (groupId) {
    formData.append("group_id", groupId);
  }
  if (groupOrder !== undefined) {
    formData.append("group_order", String(groupOrder));
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/spaces/${spaceId}/upload`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || `Upload failed (${xhr.status})`));
        } catch {
          reject(new Error(`Upload failed (${xhr.status})`));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

export function listItems(
  spaceId: string,
  contentType?: ContentType,
  page = 1,
  pageSize = 50,
): Promise<MediaItemListResponse> {
  const params = new URLSearchParams();
  if (contentType) params.set("content_type", contentType);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return apiFetch<MediaItemListResponse>(`/spaces/${spaceId}/items?${params}`);
}

export function getItem(itemId: string): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/items/${itemId}`);
}

export function updateItem(itemId: string, data: MediaItemUpdate): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/items/${itemId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteItem(itemId: string): Promise<void> {
  return apiFetch<void>(`/items/${itemId}`, { method: "DELETE" });
}

export function getTranscript(itemId: string): Promise<Transcript> {
  return apiFetch<Transcript>(`/items/${itemId}/transcript`);
}

export function retranscribe(itemId: string, whisperModel?: string): Promise<MediaItem> {
  const params = whisperModel ? `?whisper_model=${whisperModel}` : "";
  return apiFetch<MediaItem>(`/items/${itemId}/transcribe${params}`, {
    method: "POST",
  });
}

export function getChatMessages(itemId: string): Promise<ChatMessagesResponse> {
  return apiFetch<ChatMessagesResponse>(`/items/${itemId}/chat-messages`);
}

export function updateChatMessage(
  itemId: string,
  messageId: string,
  data: ChatMessageUpdate,
): Promise<ChatMessage> {
  return apiFetch<ChatMessage>(`/items/${itemId}/chat-messages/${messageId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function rerunOcr(itemId: string): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/items/${itemId}/ocr`, {
    method: "POST",
  });
}

// Group & Stitch API

export function createGroup(itemIds: string[]): Promise<MediaItem[]> {
  return apiFetch<MediaItem[]>("/groups/create", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export function ungroupItems(groupId: string): Promise<void> {
  return apiFetch<void>(`/groups/${groupId}`, { method: "DELETE" });
}

export function getGroupItems(groupId: string): Promise<MediaItem[]> {
  return apiFetch<MediaItem[]>(`/groups/${groupId}/items`);
}

export function reorderGroup(groupId: string, itemIds: string[]): Promise<MediaItem[]> {
  return apiFetch<MediaItem[]>(`/groups/${groupId}/reorder`, {
    method: "PUT",
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export function stitchGroup(groupId: string, autoOcr = true): Promise<{ status: string; task_id: string; group_id: string }> {
  return apiFetch(`/groups/${groupId}/stitch?auto_ocr=${autoOcr}`, {
    method: "POST",
  });
}
