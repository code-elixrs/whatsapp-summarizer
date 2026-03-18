import { useCallback, useRef, useState } from "react";
import type { ContentType, UploadingFile } from "../../types/media";
import { uploadFile } from "../../lib/media";
import styles from "./UploadZone.module.css";

interface UploadZoneProps {
  spaceId: string;
  onUploadComplete: () => void;
}

const CONTENT_TYPES: { value: ContentType; label: string }[] = [
  { value: "call_recording", label: "Call Recording" },
  { value: "chat_screenshot", label: "Chat Screenshot" },
  { value: "status_update", label: "Status Update" },
  { value: "other_media", label: "Other Media" },
];

export function UploadZone({ spaceId, onUploadComplete }: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedType, setSelectedType] = useState<ContentType>("other_media");
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: UploadingFile[] = Array.from(fileList).map((file) => ({
        id: crypto.randomUUID(),
        file,
        contentType: selectedType,
        timestamp: new Date().toISOString().slice(0, 16),
        status: "uploading" as const,
        progress: 0,
      }));

      setFiles((prev) => [...prev, ...newFiles]);

      newFiles.forEach((uf) => {
        uploadFile(
          spaceId,
          uf.file,
          uf.contentType,
          new Date(uf.timestamp).toISOString(),
          (progress) => {
            setFiles((prev) =>
              prev.map((f) => (f.id === uf.id ? { ...f, progress } : f))
            );
          }
        )
          .then(() => {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === uf.id ? { ...f, status: "done", progress: 100 } : f
              )
            );
            onUploadComplete();
          })
          .catch((err) => {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === uf.id
                  ? { ...f, status: "error", error: err.message }
                  : f
              )
            );
          });
      });
    },
    [spaceId, selectedType, onUploadComplete]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles]
  );

  const doneCount = files.filter((f) => f.status === "done").length;
  const hasQueue = files.length > 0;

  return (
    <div className={styles.container}>
      <div className={styles.typeSelector}>
        {CONTENT_TYPES.map((ct) => (
          <button
            key={ct.value}
            type="button"
            className={`${styles.typeChip} ${selectedType === ct.value ? styles.typeActive : ""}`}
            onClick={() => setSelectedType(ct.value)}
          >
            {ct.label}
          </button>
        ))}
      </div>

      <div
        className={`${styles.dropZone} ${dragOver ? styles.dropZoneActive : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className={styles.dropIcon}>+</div>
        <div className={styles.dropText}>
          Drop files here or click to browse
        </div>
        <div className={styles.dropHint}>
          Images, audio, video — up to 500MB each
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,audio/*,video/*"
          className={styles.hiddenInput}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFiles(e.target.files);
              e.target.value = "";
            }
          }}
        />
      </div>

      {hasQueue && (
        <div className={styles.queue}>
          <div className={styles.queueHeader}>
            <span>
              {doneCount}/{files.length} uploaded
            </span>
            {doneCount === files.length && (
              <button
                className={styles.clearBtn}
                onClick={() => setFiles([])}
              >
                Clear
              </button>
            )}
          </div>
          {files.map((uf) => (
            <div key={uf.id} className={styles.fileItem}>
              <div className={styles.fileIcon}>
                {uf.file.type.startsWith("image/")
                  ? "IMG"
                  : uf.file.type.startsWith("audio/")
                    ? "AUD"
                    : uf.file.type.startsWith("video/")
                      ? "VID"
                      : "FILE"}
              </div>
              <div className={styles.fileInfo}>
                <div className={styles.fileName}>{uf.file.name}</div>
                <div className={styles.fileMeta}>
                  {formatSize(uf.file.size)}
                </div>
              </div>
              <div className={styles.fileProgress}>
                {uf.status === "uploading" && (
                  <>
                    <div className={styles.progressBar}>
                      <div
                        className={styles.progressFill}
                        style={{ width: `${uf.progress}%` }}
                      />
                    </div>
                    <span className={styles.progressLabel}>{uf.progress}%</span>
                  </>
                )}
                {uf.status === "done" && (
                  <span className={styles.statusDone}>Done</span>
                )}
                {uf.status === "error" && (
                  <span className={styles.statusError} title={uf.error}>
                    Failed
                  </span>
                )}
              </div>
            </div>
          ))}
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
