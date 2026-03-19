import { useState } from "react";
import type { MediaItem, MediaItemUpdate } from "../../types/media";
import { updateItem } from "../../lib/media";
import styles from "./StatusGallery.module.css";

const PLATFORMS = ["all", "whatsapp", "instagram", "snapchat", "telegram", "signal"] as const;

const PLATFORM_COLORS: Record<string, string> = {
  whatsapp: "#25D366",
  instagram: "#E1306C",
  snapchat: "#FFFC00",
  telegram: "#0088cc",
  signal: "#3A76F0",
};

type GallerySize = "small" | "medium" | "large";

interface StatusGalleryProps {
  items: MediaItem[];
  onUpdate: () => void;
}

export function StatusGallery({ items, onUpdate }: StatusGalleryProps) {
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [gallerySize, setGallerySize] = useState<GallerySize>("medium");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingTimestamp, setEditingTimestamp] = useState<string | null>(null);
  const [timeValue, setTimeValue] = useState("");

  const filtered = platformFilter === "all"
    ? items
    : items.filter((i) => i.platform?.toLowerCase() === platformFilter);

  // Sort by timestamp (newest first), then created_at
  const sorted = [...filtered].sort((a, b) => {
    const tA = a.item_timestamp || a.created_at;
    const tB = b.item_timestamp || b.created_at;
    return new Date(tB).getTime() - new Date(tA).getTime();
  });

  async function handleTimestampSave(itemId: string) {
    const update: MediaItemUpdate = {
      item_timestamp: timeValue ? new Date(timeValue).toISOString() : null,
      timestamp_source: "user_provided",
    };
    await updateItem(itemId, update);
    setEditingTimestamp(null);
    onUpdate();
  }

  const sizeClass = styles[`size_${gallerySize}`];

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.platformFilters}>
          {PLATFORMS.map((p) => (
            <button
              key={p}
              className={`${styles.platformChip} ${platformFilter === p ? styles.platformActive : ""}`}
              style={
                p !== "all" && platformFilter === p
                  ? { borderColor: PLATFORM_COLORS[p], color: PLATFORM_COLORS[p] === "#FFFC00" ? "#000" : PLATFORM_COLORS[p] }
                  : undefined
              }
              onClick={() => setPlatformFilter(p)}
            >
              {p === "all" ? "All" : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        <div className={styles.sizeControls}>
          <button
            className={`${styles.sizeBtn} ${gallerySize === "small" ? styles.sizeBtnActive : ""}`}
            onClick={() => setGallerySize("small")}
            title="Small"
          >
            S
          </button>
          <button
            className={`${styles.sizeBtn} ${gallerySize === "medium" ? styles.sizeBtnActive : ""}`}
            onClick={() => setGallerySize("medium")}
            title="Medium"
          >
            M
          </button>
          <button
            className={`${styles.sizeBtn} ${gallerySize === "large" ? styles.sizeBtnActive : ""}`}
            onClick={() => setGallerySize("large")}
            title="Large"
          >
            L
          </button>
        </div>
      </div>

      {sorted.length === 0 ? (
        <div className={styles.empty}>
          No status updates{platformFilter !== "all" ? ` from ${platformFilter}` : ""}
        </div>
      ) : (
        <div className={`${styles.masonry} ${sizeClass}`}>
          {sorted.map((item) => {
            const isImage = item.mime_type.startsWith("image/");
            const isVideo = item.mime_type.startsWith("video/");
            const isExpanded = expandedId === item.id;
            const platformColor = item.platform
              ? PLATFORM_COLORS[item.platform.toLowerCase()]
              : undefined;

            const formattedTime = item.item_timestamp
              ? new Date(item.item_timestamp).toLocaleString("en-IN", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })
              : "No timestamp";

            return (
              <div key={item.id} className={styles.card}>
                <div
                  className={styles.mediaWrapper}
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                >
                  {isImage && (
                    <img
                      src={item.file_url}
                      alt={item.title || item.file_name}
                      className={styles.media}
                      loading="lazy"
                    />
                  )}
                  {isVideo && (
                    isExpanded ? (
                      <video
                        controls
                        autoPlay
                        className={styles.media}
                        preload="metadata"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <source src={item.file_url} type={item.mime_type} />
                      </video>
                    ) : (
                      <div className={styles.videoThumb}>
                        <video src={item.file_url} className={styles.media} preload="metadata" />
                        <span className={styles.playIcon}>&#9654;</span>
                      </div>
                    )
                  )}
                  {!isImage && !isVideo && (
                    <div className={styles.filePlaceholder}>
                      {item.file_name}
                    </div>
                  )}
                </div>

                <div className={styles.cardFooter}>
                  {item.platform && (
                    <span
                      className={styles.platformTag}
                      style={platformColor ? { background: platformColor, color: platformColor === "#FFFC00" ? "#000" : "#fff" } : undefined}
                    >
                      {item.platform}
                    </span>
                  )}

                  {editingTimestamp === item.id ? (
                    <div className={styles.timestampEdit} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="datetime-local"
                        className={styles.timestampInput}
                        value={timeValue}
                        onChange={(e) => setTimeValue(e.target.value)}
                        onBlur={() => handleTimestampSave(item.id)}
                        onKeyDown={(e) => e.key === "Enter" && handleTimestampSave(item.id)}
                        autoFocus
                      />
                    </div>
                  ) : (
                    <button
                      className={styles.timestampBtn}
                      onClick={() => {
                        setEditingTimestamp(item.id);
                        setTimeValue(item.item_timestamp ? item.item_timestamp.slice(0, 16) : "");
                      }}
                    >
                      {formattedTime}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Expanded overlay */}
      {expandedId && (
        <div className={styles.overlay} onClick={() => setExpandedId(null)}>
          <div className={styles.overlayContent} onClick={(e) => e.stopPropagation()}>
            {(() => {
              const item = sorted.find((i) => i.id === expandedId);
              if (!item) return null;
              const isImage = item.mime_type.startsWith("image/");
              const isVideo = item.mime_type.startsWith("video/");
              return (
                <>
                  {isImage && (
                    <img src={item.file_url} alt={item.title || item.file_name} className={styles.overlayMedia} />
                  )}
                  {isVideo && (
                    <video controls autoPlay className={styles.overlayMedia} preload="metadata">
                      <source src={item.file_url} type={item.mime_type} />
                    </video>
                  )}
                  <button className={styles.overlayClose} onClick={() => setExpandedId(null)}>
                    &times;
                  </button>
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
