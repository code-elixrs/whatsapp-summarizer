import { useCallback, useEffect, useState } from "react";
import type { ChatStreamEntry, ChatStreamResponse } from "../../types/media";
import { getChatStream } from "../../lib/media";
import { EventMarker } from "./EventMarker";
import styles from "./UnifiedChatView.module.css";

interface UnifiedChatViewProps {
  spaceId: string;
}

export function UnifiedChatView({ spaceId }: UnifiedChatViewProps) {
  const [stream, setStream] = useState<ChatStreamResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getChatStream(spaceId);
      setStream(data);
    } catch {
      setError("Failed to load chat stream");
    } finally {
      setLoading(false);
    }
  }, [spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <div className={styles.loading}>Loading conversation...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!stream || stream.entries.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyTitle}>No conversation yet</p>
        <p className={styles.emptyHint}>Upload chat screenshots to see the unified conversation view</p>
      </div>
    );
  }

  // Group consecutive messages from the same source group for source indicators
  const groupedEntries = groupBySource(stream.entries);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.stats}>
          {stream.total_messages} messages
          {stream.total_events > 0 && ` · ${stream.total_events} events`}
        </span>
      </div>
      <div className={styles.conversation}>
        {groupedEntries.map((group, gIdx) => (
          <div key={gIdx}>
            {group.sourceLabel && (
              <div className={styles.sourceIndicator}>
                <div className={styles.sourceLine} />
                <span className={styles.sourceLabel}>{group.sourceLabel}</span>
                <div className={styles.sourceLine} />
              </div>
            )}
            {group.entries.map((entry, eIdx) =>
              entry.type === "event" ? (
                <EventMarker key={`event-${gIdx}-${eIdx}`} event={entry} />
              ) : (
                <div
                  key={`msg-${entry.id}`}
                  className={`${styles.bubbleRow} ${entry.is_sent ? styles.sent : styles.received}`}
                >
                  <div className={`${styles.bubble} ${entry.is_sent ? styles.bubbleSent : styles.bubbleReceived}`}>
                    {!entry.is_sent && entry.sender && (
                      <div className={styles.sender}>{entry.sender}</div>
                    )}
                    <div className={styles.messageText}>{entry.message}</div>
                    <div className={styles.meta}>
                      {entry.message_timestamp && (
                        <span className={styles.timestamp}>
                          {new Date(entry.message_timestamp).toLocaleTimeString("en-IN", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface EntryGroup {
  sourceLabel: string | null;
  entries: ChatStreamEntry[];
}

function groupBySource(entries: ChatStreamEntry[]): EntryGroup[] {
  const groups: EntryGroup[] = [];
  let currentGroupId: string | null | undefined = undefined;
  let currentGroup: EntryGroup | null = null;

  for (const entry of entries) {
    if (entry.type === "event") {
      // Events always get their own "group" (no source label)
      if (currentGroup) {
        groups.push(currentGroup);
      }
      groups.push({ sourceLabel: null, entries: [entry] });
      currentGroup = null;
      currentGroupId = undefined;
    } else {
      const entryGroupId = entry.source_group_id;
      if (entryGroupId !== currentGroupId) {
        if (currentGroup) {
          groups.push(currentGroup);
        }
        const label = entryGroupId
          ? `Screenshot Group`
          : null;
        currentGroup = { sourceLabel: label, entries: [entry] };
        currentGroupId = entryGroupId;
      } else {
        currentGroup!.entries.push(entry);
      }
    }
  }

  if (currentGroup) {
    groups.push(currentGroup);
  }

  return groups;
}
