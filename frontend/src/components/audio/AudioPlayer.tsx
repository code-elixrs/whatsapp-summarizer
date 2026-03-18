import { useCallback, useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import type { TranscriptSegment } from "../../types/media";
import styles from "./AudioPlayer.module.css";

interface AudioPlayerProps {
  fileUrl: string;
  segments: TranscriptSegment[];
  onTimeUpdate?: (time: number) => void;
  onSeek?: (time: number) => void;
}

export function AudioPlayer({ fileUrl, segments, onTimeUpdate, onSeek }: AudioPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(-1);

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
      height: 64,
      normalize: true,
      backend: "WebAudio",
    });

    ws.load(fileUrl);

    ws.on("ready", () => {
      setDuration(ws.getDuration());
    });

    ws.on("audioprocess", () => {
      const time = ws.getCurrentTime();
      setCurrentTime(time);
      onTimeUpdate?.(time);
    });

    ws.on("seeking", () => {
      const time = ws.getCurrentTime();
      setCurrentTime(time);
      onSeek?.(time);
    });

    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));

    wavesurferRef.current = ws;

    return () => {
      ws.destroy();
      wavesurferRef.current = null;
    };
  }, [fileUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // Track active segment
  useEffect(() => {
    const idx = segments.findIndex(
      (s) => currentTime >= s.start_time && currentTime < s.end_time
    );
    if (idx !== activeSegmentIndex) {
      setActiveSegmentIndex(idx);
    }
  }, [currentTime, segments, activeSegmentIndex]);

  const togglePlay = useCallback(() => {
    wavesurferRef.current?.playPause();
  }, []);

  const seekTo = useCallback((time: number) => {
    const ws = wavesurferRef.current;
    if (ws && duration > 0) {
      ws.seekTo(time / duration);
      onSeek?.(time);
    }
  }, [duration, onSeek]);

  const changeRate = useCallback(() => {
    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    const newRate = rates[nextIdx];
    setPlaybackRate(newRate);
    wavesurferRef.current?.setPlaybackRate(newRate);
  }, [playbackRate]);

  const skip = useCallback((seconds: number) => {
    const ws = wavesurferRef.current;
    if (ws) {
      const newTime = Math.max(0, Math.min(ws.getCurrentTime() + seconds, duration));
      ws.seekTo(newTime / duration);
    }
  }, [duration]);

  return (
    <div className={styles.player}>
      <div ref={containerRef} className={styles.waveform} />
      <div className={styles.controls}>
        <div className={styles.leftControls}>
          <button className={styles.controlBtn} onClick={() => skip(-10)} title="Back 10s">
            -10s
          </button>
          <button className={styles.playBtn} onClick={togglePlay}>
            {isPlaying ? "\u275A\u275A" : "\u25B6"}
          </button>
          <button className={styles.controlBtn} onClick={() => skip(10)} title="Forward 10s">
            +10s
          </button>
        </div>
        <div className={styles.timeDisplay}>
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>
        <button className={styles.rateBtn} onClick={changeRate} title="Playback speed">
          {playbackRate}x
        </button>
      </div>
    </div>
  );
}

// Expose seekTo via a hook-friendly pattern
export function useAudioPlayerSeek() {
  const seekFnRef = useRef<((time: number) => void) | null>(null);
  return {
    seekRef: seekFnRef,
    seekTo: (time: number) => seekFnRef.current?.(time),
  };
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
