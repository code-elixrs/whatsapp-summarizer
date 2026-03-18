import { useCallback, useEffect, useState } from "react";
import type { MediaItem, ChatMessage, ChatMessagesResponse, OCRStatus } from "../../types/media";
import { getChatMessages, rerunOcr, updateChatMessage } from "../../lib/media";
import { ChatBubbleView } from "./ChatBubbleView";
import styles from "./ChatDetailView.module.css";

interface ChatDetailViewProps {
  item: MediaItem;
  onUpdate: () => void;
}

type TabView = "chat" | "screenshot" | "split";

export function ChatDetailView({ item, onUpdate }: ChatDetailViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabView>("chat");

  const [wsStatus, setWsStatus] = useState<OCRStatus | null>(null);

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

  const isProcessing = item.processing_status === "pending" || item.processing_status === "processing";

  return (
    <div className={styles.container}>
      {/* Tab switcher */}
      {!isProcessing && item.processing_status !== "failed" && (
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === "chat" ? styles.tabActive : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            Chat View
          </button>
          <button
            className={`${styles.tab} ${activeTab === "screenshot" ? styles.tabActive : ""}`}
            onClick={() => setActiveTab("screenshot")}
          >
            Original
          </button>
          <button
            className={`${styles.tab} ${activeTab === "split" ? styles.tabActive : ""}`}
            onClick={() => setActiveTab("split")}
          >
            Split View
          </button>
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

          {(activeTab === "screenshot" || activeTab === "split") && (
            <div className={styles.screenshotPanel}>
              <img
                src={item.file_url}
                alt={item.file_name}
                className={styles.screenshotImg}
                loading="lazy"
              />
            </div>
          )}
        </div>
      )}

      {/* Re-run OCR */}
      {item.processing_status === "completed" && (
        <div className={styles.rerunSection}>
          <button className={styles.rerunBtn} onClick={handleRerunOcr}>
            Re-run OCR
          </button>
        </div>
      )}
    </div>
  );
}
