import { useEffect, useMemo, useRef, useState } from "react";
import type { TranscriptSegment } from "../../types/media";
import styles from "./TranscriptView.module.css";

interface TranscriptViewProps {
  segments: TranscriptSegment[];
  currentTime: number;
  onSeek: (time: number) => void;
  language?: string | null;
}

export function TranscriptView({ segments, currentTime, onSeek, language }: TranscriptViewProps) {
  const [search, setSearch] = useState("");
  const activeRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const activeIndex = useMemo(() => {
    return segments.findIndex(
      (s) => currentTime >= s.start_time && currentTime < s.end_time
    );
  }, [segments, currentTime]);

  const filteredSegments = useMemo(() => {
    if (!search.trim()) return segments;
    const q = search.toLowerCase();
    return segments.filter((s) => s.text.toLowerCase().includes(q));
  }, [segments, search]);

  const matchCount = search.trim() ? filteredSegments.length : 0;

  // Auto-scroll to active segment
  useEffect(() => {
    if (autoScroll && activeRef.current && containerRef.current) {
      activeRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [activeIndex, autoScroll]);

  // Detect manual scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let timeout: number;
    const handleScroll = () => {
      setAutoScroll(false);
      clearTimeout(timeout);
      timeout = window.setTimeout(() => setAutoScroll(true), 5000);
    };
    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      container.removeEventListener("scroll", handleScroll);
      clearTimeout(timeout);
    };
  }, []);

  function highlightText(text: string): React.ReactNode {
    if (!search.trim()) return text;
    const q = search.toLowerCase();
    const idx = text.toLowerCase().indexOf(q);
    if (idx === -1) return text;
    return (
      <>
        {text.slice(0, idx)}
        <mark className={styles.highlight}>{text.slice(idx, idx + search.length)}</mark>
        {text.slice(idx + search.length)}
      </>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.searchWrap}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search transcript..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search.trim() && (
            <span className={styles.matchCount}>
              {matchCount} match{matchCount !== 1 ? "es" : ""}
            </span>
          )}
        </div>
        {language && (
          <span className={styles.langBadge}>{language.toUpperCase()}</span>
        )}
      </div>

      <div className={styles.segments} ref={containerRef}>
        {filteredSegments.length === 0 ? (
          <div className={styles.empty}>
            {search.trim() ? "No matches found" : "No transcript segments"}
          </div>
        ) : (
          filteredSegments.map((seg) => {
            const isActive = seg.segment_index === activeIndex;
            return (
              <div
                key={seg.id}
                ref={isActive && !search.trim() ? activeRef : null}
                className={`${styles.segment} ${isActive ? styles.segmentActive : ""}`}
                onClick={() => onSeek(seg.start_time)}
              >
                <span className={styles.timestamp}>
                  {formatTime(seg.start_time)}
                </span>
                <span className={styles.text}>{highlightText(seg.text)}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
