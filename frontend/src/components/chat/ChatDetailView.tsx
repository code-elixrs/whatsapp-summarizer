import { useCallback, useEffect, useState } from "react";
import type { MediaItem, ChatMessage, OCRStatus, StitchStatus } from "../../types/media";
import { getChatMessages, rerunOcr, updateChatMessage, getGroupItems, stitchGroup, reorderGroup } from "../../lib/media";
import { ChatBubbleView } from "./ChatBubbleView";
import styles from "./ChatDetailView.module.css";

interface ChatDetailViewProps {
  item: MediaItem;
  onUpdate: () => void;
}

type TabView = "chat" | "stitched" | "screenshot" | "split";

export function ChatDetailView({ item, onUpdate }: ChatDetailViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabView>("chat");

  const [wsStatus, setWsStatus] = useState<OCRStatus | null>(null);
  const [stitchWsStatus, setStitchWsStatus] = useState<StitchStatus | null>(null);

  const [groupItems, setGroupItems] = useState<MediaItem[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const hasGroup = !!item.group_id;
  const hasStitch = !!item.stitched_path;

  // Load chat messages
  const loadMessages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getChatMessages(item.id);
      setMessages(data.messages);
    } catch {
      setError("No chat messages available");
    } finally {
      setLoading(false);
    }
  }, [item.id]);

  useEffect(() => {
    if (item.processing_status === "completed") {
      loadMessages();
    }
  }, [item.id, item.processing_status, loadMessages]);

  // Load group items
  useEffect(() => {
    if (item.group_id) {
      getGroupItems(item.group_id).then(setGroupItems).catch(() => {});
    }
  }, [item.group_id]);

  // WebSocket for OCR progress
  useEffect(() => {
    if (item.processing_status !== "pending" && item.processing_status !== "processing") {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/ocr/${item.id}`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const data: OCRStatus = JSON.parse(event.data);
      setWsStatus(data);

      if (data.status === "completed") {
        onUpdate();
        loadMessages();
      }
    };

    socket.onerror = () => setWsStatus(null);

    return () => {
      socket.close();
    };
  }, [item.id, item.processing_status, onUpdate, loadMessages]);

  async function handleRerunOcr() {
    try {
      await rerunOcr(item.id);
      setMessages([]);
      setError(null);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start OCR");
    }
  }

  async function handleMessageUpdate(messageId: string, field: string, value: string | boolean) {
    try {
      const updated = await updateChatMessage(item.id, messageId, { [field]: value });
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? updated : m))
      );
    } catch {
      // silently fail for inline edits
    }
  }

  async function handleStitch() {
    if (!item.group_id) return;
    try {
      await stitchGroup(item.group_id);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start stitching");
    }
  }

  // Drag-reorder handlers for group items
  function handleDragStart(idx: number) {
    setDragIdx(idx);
  }

  function handleDragOver(e: React.DragEvent, idx: number) {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
    const reordered = [...groupItems];
    const [moved] = reordered.splice(dragIdx, 1);
    reordered.splice(idx, 0, moved);
    setGroupItems(reordered);
    setDragIdx(idx);
  }

  async function handleDragEnd() {
    setDragIdx(null);
    if (!item.group_id || groupItems.length < 2) return;
    try {
      await reorderGroup(item.group_id, groupItems.map((i) => i.id));
      onUpdate();
    } catch {
      // reload original order
      if (item.group_id) {
        getGroupItems(item.group_id).then(setGroupItems).catch(() => {});
      }
    }
  }

  const isProcessing = item.processing_status === "pending" || item.processing_status === "processing";

  // Determine available tabs
  const tabs: { key: TabView; label: string }[] = [
    { key: "chat", label: "Chat View" },
  ];
  if (hasStitch) {
    tabs.push({ key: "stitched", label: "Stitched" });
  }
  if (hasGroup && groupItems.length > 1) {
    tabs.push({ key: "screenshot", label: `Originals (${groupItems.length})` });
  } else {
    tabs.push({ key: "screenshot", label: "Original" });
  }
  tabs.push({ key: "split", label: "Split View" });

  return (
    <div className={styles.container}>
      {/* Tab switcher */}
      {!isProcessing && item.processing_status !== "failed" && (
        <div className={styles.tabs}>
          {tabs.map((t) => (
            <button
              key={t.key}
              className={`${styles.tab} ${activeTab === t.key ? styles.tabActive : ""}`}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {/* OCR Progress */}
      {isProcessing && (
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressLabel}>
              {wsStatus?.status === "ocr_processing" ? "Processing screenshot..." : "Waiting to start..."}
            </span>
            <span className={styles.progressPercent}>{wsStatus?.progress ?? 0}%</span>
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${wsStatus?.progress ?? 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Failed state */}
      {item.processing_status === "failed" && (
        <div className={styles.failedSection}>
          <span>OCR processing failed</span>
          <button className={styles.retryBtn} onClick={handleRerunOcr}>
            Retry
          </button>
        </div>
      )}

      {/* Content area */}
      {!isProcessing && item.processing_status !== "failed" && (
        <div className={`${styles.content} ${activeTab === "split" ? styles.contentSplit : ""}`}>
          {(activeTab === "chat" || activeTab === "split") && (
            <div className={styles.chatPanel}>
              {loading && <div className={styles.loadingText}>Loading messages...</div>}
              {!loading && messages.length > 0 && (
                <ChatBubbleView
                  messages={messages}
                  onUpdateMessage={handleMessageUpdate}
                />
              )}
              {!loading && messages.length === 0 && !error && (
                <div className={styles.emptyState}>No messages extracted</div>
              )}
              {error && <div className={styles.errorText}>{error}</div>}
            </div>
          )}

          {/* Stitched image tab */}
          {activeTab === "stitched" && hasStitch && item.group_id && (
            <div className={styles.screenshotPanel}>
              <img
                src={`/api/files/stitched/${item.group_id}`}
                alt="Stitched screenshot"
                className={styles.screenshotImg}
                loading="lazy"
              />
            </div>
          )}

          {/* Originals tab - shows all group items or single screenshot */}
          {activeTab === "screenshot" && (
            <div className={styles.originalsPanel}>
              {hasGroup && groupItems.length > 1 ? (
                <>
                  <div className={styles.originalsHint}>Drag to reorder, then re-stitch</div>
                  {groupItems.map((gi, idx) => (
                    <div
                      key={gi.id}
                      className={`${styles.originalItem} ${dragIdx === idx ? styles.originalItemDragging : ""}`}
                      draggable
                      onDragStart={() => handleDragStart(idx)}
                      onDragOver={(e) => handleDragOver(e, idx)}
                      onDragEnd={handleDragEnd}
                    >
                      <span className={styles.originalOrder}>{idx + 1}</span>
                      <img
                        src={gi.file_url}
                        alt={gi.file_name}
                        className={styles.originalThumb}
                        loading="lazy"
                      />
                      <span className={styles.originalName}>{gi.file_name}</span>
                    </div>
                  ))}
                </>
              ) : (
                <img
                  src={item.file_url}
                  alt={item.file_name}
                  className={styles.screenshotImg}
                  loading="lazy"
                />
              )}
            </div>
          )}

          {/* Split view - show stitched or original alongside chat */}
          {activeTab === "split" && (
            <div className={styles.screenshotPanel}>
              <img
                src={hasStitch && item.group_id ? `/api/files/stitched/${item.group_id}` : item.file_url}
                alt={item.file_name}
                className={styles.screenshotImg}
                loading="lazy"
              />
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      {item.processing_status === "completed" && (
        <div className={styles.rerunSection}>
          {hasGroup && groupItems.length > 1 && (
            <button className={styles.stitchBtn} onClick={handleStitch}>
              {hasStitch ? "Re-stitch" : "Stitch Screenshots"}
            </button>
          )}
          <button className={styles.rerunBtn} onClick={handleRerunOcr}>
            Re-run OCR
          </button>
        </div>
      )}
    </div>
  );
}
