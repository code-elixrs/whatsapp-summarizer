import { useCallback, useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import type { MediaItem, Transcript, TranscriptionStatus } from "../../types/media";
import { getTranscript, retranscribe } from "../../lib/media";
import { TranscriptView } from "./TranscriptView";
import styles from "./CallDetailView.module.css";

interface CallDetailViewProps {
  item: MediaItem;
  onUpdate: () => void;
}

const WHISPER_MODELS = [
  { value: "tiny", label: "Tiny (fastest)" },
  { value: "base", label: "Base (default)" },
  { value: "small", label: "Small (better)" },
  { value: "medium", label: "Medium (best CPU)" },
  { value: "large-v3", label: "Large v3 (GPU)" },
];

export function CallDetailView({ item, onUpdate }: CallDetailViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);

  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);

  const [wsStatus, setWsStatus] = useState<TranscriptionStatus | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [selectedModel, setSelectedModel] = useState("base");

  // Initialize wavesurfer
  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "rgba(124, 58, 237, 0.4)",
      progressColor: "#7c3aed",
      cursorColor: "#8b5cf6",
      cursorWidth: 2,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 72,
      normalize: true,
      backend: "WebAudio",
    });

    ws.load(item.file_url);
    ws.on("ready", () => setDuration(ws.getDuration()));
    ws.on("audioprocess", () => setCurrentTime(ws.getCurrentTime()));
    ws.on("seeking", () => setCurrentTime(ws.getCurrentTime()));
    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));

    wavesurferRef.current = ws;
    return () => {
      ws.destroy();
      wavesurferRef.current = null;
    };
  }, [item.file_url]);

  // Load transcript
  useEffect(() => {
    if (item.processing_status === "completed") {
      setTranscriptLoading(true);
      getTranscript(item.id)
        .then(setTranscript)
        .catch(() => setTranscriptError("No transcript available"))
        .finally(() => setTranscriptLoading(false));
    }
  }, [item.id, item.processing_status]);

  // WebSocket for transcription progress
  useEffect(() => {
    if (item.processing_status !== "pending" && item.processing_status !== "processing") {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/transcription/${item.id}`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const data: TranscriptionStatus = JSON.parse(event.data);
      setWsStatus(data);

      if (data.status === "completed") {
        onUpdate();
        // Load transcript after completion
        getTranscript(item.id)
          .then(setTranscript)
          .catch(() => {});
      }
    };

    socket.onerror = () => {
      setWsStatus(null);
    };

    wsRef.current = socket;
    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [item.id, item.processing_status, onUpdate]);

  const seekTo = useCallback((time: number) => {
    const ws = wavesurferRef.current;
    if (ws && duration > 0) {
      ws.seekTo(time / duration);
    }
  }, [duration]);

  const togglePlay = useCallback(() => {
    wavesurferRef.current?.playPause();
  }, []);

  const skip = useCallback((seconds: number) => {
    const ws = wavesurferRef.current;
    if (ws && duration > 0) {
      const newTime = Math.max(0, Math.min(ws.getCurrentTime() + seconds, duration));
      ws.seekTo(newTime / duration);
    }
  }, [duration]);

  const changeRate = useCallback(() => {
    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    const newRate = rates[nextIdx];
    setPlaybackRate(newRate);
    wavesurferRef.current?.setPlaybackRate(newRate);
  }, [playbackRate]);

  async function handleRetranscribe() {
    try {
      await retranscribe(item.id, selectedModel);
      setTranscript(null);
      setTranscriptError(null);
      onUpdate();
    } catch (err) {
      setTranscriptError(err instanceof Error ? err.message : "Failed to start transcription");
    }
  }

  const isTranscribing = item.processing_status === "pending" || item.processing_status === "processing";

  return (
    <div className={styles.container}>
      {/* Waveform Player */}
      <div className={styles.playerSection}>
        <div ref={containerRef} className={styles.waveform} />
        <div className={styles.controls}>
          <div className={styles.leftControls}>
            <button className={styles.controlBtn} onClick={() => skip(-10)}>-10s</button>
            <button className={styles.playBtn} onClick={togglePlay}>
              {isPlaying ? "\u275A\u275A" : "\u25B6"}
            </button>
            <button className={styles.controlBtn} onClick={() => skip(10)}>+10s</button>
          </div>
          <div className={styles.timeDisplay}>
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
          <button className={styles.rateBtn} onClick={changeRate}>{playbackRate}x</button>
        </div>
      </div>

      {/* Transcription Progress */}
      {isTranscribing && (
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressLabel}>
              {wsStatus?.status === "transcribing" ? "Transcribing..." : "Waiting to start..."}
            </span>
            <span className={styles.progressPercent}>{wsStatus?.progress ?? 0}%</span>
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${wsStatus?.progress ?? 0}%` }}
            />
          </div>
          {wsStatus?.segments_done && (
            <span className={styles.progressMeta}>
              {wsStatus.segments_done} segments processed
            </span>
          )}
        </div>
      )}

      {/* Failed state */}
      {item.processing_status === "failed" && (
        <div className={styles.failedSection}>
          <span>Transcription failed</span>
          <button className={styles.retryBtn} onClick={handleRetranscribe}>
            Retry
          </button>
        </div>
      )}

      {/* Transcript */}
      {transcript && transcript.segments.length > 0 && (
        <div className={styles.transcriptSection}>
          <TranscriptView
            segments={transcript.segments}
            currentTime={currentTime}
            onSeek={seekTo}
            language={transcript.language}
          />
        </div>
      )}

      {/* Retranscribe controls */}
      {item.processing_status === "completed" && (
        <div className={styles.retranscribeSection}>
          <select
            className={styles.modelSelect}
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {WHISPER_MODELS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <button className={styles.retranscribeBtn} onClick={handleRetranscribe}>
            Re-transcribe
          </button>
        </div>
      )}

      {transcriptLoading && (
        <div className={styles.loadingText}>Loading transcript...</div>
      )}
      {transcriptError && !isTranscribing && item.processing_status !== "failed" && (
        <div className={styles.noTranscript}>{transcriptError}</div>
      )}
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
