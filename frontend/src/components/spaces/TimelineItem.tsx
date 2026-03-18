import { useState } from "react";
import type { MediaItem, MediaItemUpdate } from "../../types/media";
import { updateItem, deleteItem } from "../../lib/media";
import { CallDetailView } from "../audio/CallDetailView";
import { ChatDetailView } from "../chat/ChatDetailView";
import styles from "./TimelineItem.module.css";

interface TimelineItemProps {
  item: MediaItem;
  onUpdate: () => void;
}

const TYPE_LABELS: Record<string, { label: string; className: string }> = {
  call_recording: { label: "CALL", className: "badgeCall" },
  chat_screenshot: { label: "CHAT", className: "badgeChat" },
  status_update: { label: "STATUS", className: "badgeStatus" },
  other_media: { label: "MEDIA", className: "badgeMedia" },
};

export function TimelineItem({ item, onUpdate }: TimelineItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [editingTime, setEditingTime] = useState(false);
  const [timeValue, setTimeValue] = useState(
    item.item_timestamp ? item.item_timestamp.slice(0, 16) : ""
  );
  const [showDelete, setShowDelete] = useState(false);

  const badge = TYPE_LABELS[item.content_type] || TYPE_LABELS.other_media;

  async function handleTimeUpdate() {
    const update: MediaItemUpdate = {
      item_timestamp: timeValue ? new Date(timeValue).toISOString() : null,
      timestamp_source: "user_provided",
    };
    await updateItem(item.id, update);
    setEditingTime(false);
    onUpdate();
  }

  async function handleDelete() {
    await deleteItem(item.id);
    onUpdate();
  }

  const formattedTime = item.item_timestamp
    ? new Date(item.item_timestamp).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "No timestamp";

  const isImage = item.mime_type.startsWith("image/");
  const isAudio = item.mime_type.startsWith("audio/");
  const isVideo = item.mime_type.startsWith("video/");
  const isChatScreenshot = item.content_type === "chat_screenshot" && isImage;

  return (
    <div className={styles.item}>
      <div className={styles.header} onClick={() => setExpanded(!expanded)}>
        <span className={`${styles.badge} ${styles[badge.className]}`}>
          {badge.label}
        </span>
        <span className={styles.time}>
          {editingTime ? (
            <span onClick={(e) => e.stopPropagation()}>
              <input
                type="datetime-local"
                className={styles.timeInput}
                value={timeValue}
                onChange={(e) => setTimeValue(e.target.value)}
                onBlur={handleTimeUpdate}
                onKeyDown={(e) => e.key === "Enter" && handleTimeUpdate()}
                autoFocus
              />
            </span>
          ) : (
            <>
              {formattedTime}
              <button
                className={styles.editBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  setEditingTime(true);
                }}
              >
                edit
              </button>
            </>
          )}
        </span>
        <span className={styles.title}>
          {item.title || item.file_name}
        </span>
        {(isAudio || isChatScreenshot) && item.processing_status !== "completed" && (
          <span className={`${styles.statusBadge} ${styles[`status_${item.processing_status}`]}`}>
            {item.processing_status === "processing"
              ? (isAudio ? "Transcribing..." : "OCR Processing...")
              : item.processing_status === "pending" ? "Queued"
              : item.processing_status === "failed" ? "Failed" : ""}
          </span>
        )}
        <span className={styles.size}>{formatSize(item.file_size)}</span>
        <button
          className={styles.deleteBtn}
          onClick={(e) => {
            e.stopPropagation();
            setShowDelete(true);
          }}
        >
          &times;
        </button>
        <span className={styles.chevron}>{expanded ? "\u25B2" : "\u25BC"}</span>
      </div>

      {expanded && (
        <div className={styles.content}>
          {isChatScreenshot && (
            <ChatDetailView item={item} onUpdate={onUpdate} />
          )}
          {isImage && !isChatScreenshot && (
            <img
              src={item.file_url}
              alt={item.file_name}
              className={styles.imagePreview}
              loading="lazy"
            />
          )}
          {isAudio && (
            <CallDetailView item={item} onUpdate={onUpdate} />
          )}
          {isVideo && (
            <video controls className={styles.videoPlayer} preload="metadata">
              <source src={item.file_url} type={item.mime_type} />
            </video>
          )}
        </div>
      )}

      {showDelete && (
        <div className={styles.overlay} onClick={() => setShowDelete(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <p>Delete <strong>{item.file_name}</strong>?</p>
            <div className={styles.modalActions}>
              <button
                className={styles.cancelBtn}
                onClick={() => setShowDelete(false)}
              >
                Cancel
              </button>
              <button className={styles.confirmBtn} onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
