import { useState } from "react";
import type { ChatStreamEvent } from "../../types/media";
import styles from "./EventMarker.module.css";

const PLATFORM_COLORS: Record<string, string> = {
  whatsapp: "#25D366",
  instagram: "#E1306C",
  snapchat: "#FFFC00",
  telegram: "#0088cc",
  signal: "#3A76F0",
};

const EVENT_LABELS: Record<string, string> = {
  call_recording: "Call Recording",
  status_update: "Status Update",
  other_media: "Media",
};

interface EventMarkerProps {
  event: ChatStreamEvent;
}

export function EventMarker({ event }: EventMarkerProps) {
  const [expanded, setExpanded] = useState(false);

  const label = EVENT_LABELS[event.event_type] || "Event";
  const isCall = event.event_type === "call_recording";
  const isStatus = event.event_type === "status_update";
  const isImage = event.mime_type.startsWith("image/");
  const isVideo = event.mime_type.startsWith("video/");
  const isAudio = event.mime_type.startsWith("audio/");
  const platformColor = event.platform ? PLATFORM_COLORS[event.platform.toLowerCase()] : undefined;

  const formattedTime = event.item_timestamp
    ? new Date(event.item_timestamp).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : null;

  function formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  return (
    <div className={styles.marker}>
      <div className={styles.line} />
      <div
        className={`${styles.card} ${expanded ? styles.cardExpanded : ""}`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className={styles.cardHeader}>
          <span className={`${styles.icon} ${styles[`icon_${event.event_type}`]}`}>
            {isCall ? "\u260E" : isStatus ? "\u25CB" : "\u25A0"}
          </span>
          <span className={styles.label}>{label}</span>
          {event.platform && (
            <span
              className={styles.platformBadge}
              style={platformColor ? { background: platformColor, color: platformColor === "#FFFC00" ? "#000" : "#fff" } : undefined}
            >
              {event.platform}
            </span>
          )}
          {isCall && event.duration_seconds && (
            <span className={styles.duration}>{formatDuration(event.duration_seconds)}</span>
          )}
          {formattedTime && <span className={styles.time}>{formattedTime}</span>}
        </div>

        {expanded && (
          <div className={styles.cardBody}>
            {isImage && (
              <img src={event.file_url} alt={event.file_name} className={styles.preview} loading="lazy" />
            )}
            {isVideo && (
              <video controls className={styles.preview} preload="metadata">
                <source src={event.file_url} type={event.mime_type} />
              </video>
            )}
            {isAudio && (
              <audio controls className={styles.audioPlayer} preload="metadata">
                <source src={event.file_url} type={event.mime_type} />
              </audio>
            )}
            {event.transcript_summary && (
              <div className={styles.transcriptSummary}>
                <span className={styles.transcriptLabel}>Transcript:</span>
                {event.transcript_summary}
                {event.transcript_summary.length >= 200 && "..."}
              </div>
            )}
          </div>
        )}
      </div>
      <div className={styles.line} />
    </div>
  );
}
