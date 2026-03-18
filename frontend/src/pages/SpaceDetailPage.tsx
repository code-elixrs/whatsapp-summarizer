import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { getSpace, deleteSpace } from "../lib/spaces";
import type { Space } from "../types/space";
import styles from "./SpaceDetailPage.module.css";

export function SpaceDetailPage() {
  const { spaceId } = useParams<{ spaceId: string }>();
  const navigate = useNavigate();
  const [space, setSpace] = useState<Space | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (!spaceId) return;
    (async () => {
      try {
        const data = await getSpace(spaceId);
        setSpace(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load space");
      } finally {
        setLoading(false);
      }
    })();
  }, [spaceId]);

  async function handleDelete() {
    if (!spaceId) return;
    try {
      await deleteSpace(spaceId);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete space");
      setShowDeleteConfirm(false);
    }
  }

  if (loading) {
    return (
      <div className={styles.centered}>
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (error || !space) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          {error || "Space not found"}
          <button onClick={() => navigate("/")} className={styles.backBtn}>
            &larr; Go back
          </button>
        </div>
      </div>
    );
  }

  const initial = space.name.charAt(0).toUpperCase();
  const totalItems =
    space.item_counts.calls +
    space.item_counts.chats +
    space.item_counts.statuses +
    space.item_counts.media;

  return (
    <div className={styles.container}>
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate("/")}>
          &larr; Back
        </button>
        <div className={styles.topActions}>
          <button
            className={styles.deleteBtn}
            onClick={() => setShowDeleteConfirm(true)}
          >
            Delete
          </button>
        </div>
      </div>

      <div className={styles.spaceHeader}>
        <div className={styles.avatar} style={{ background: space.color }}>
          {initial}
        </div>
        <div>
          <h1 className={styles.spaceName}>{space.name}</h1>
          {space.description && (
            <p className={styles.spaceDesc}>{space.description}</p>
          )}
          <div className={styles.statBar}>
            <span className={styles.statItem}>{space.item_counts.calls} calls</span>
            <span className={styles.statItem}>{space.item_counts.chats} chats</span>
            <span className={styles.statItem}>{space.item_counts.statuses} statuses</span>
            <span className={styles.statItem}>{space.item_counts.media} media</span>
          </div>
        </div>
      </div>

      {/* Timeline placeholder — will be built in Milestone 3 */}
      <div className={styles.timelineSection}>
        <div className={styles.timelineHeader}>
          <h2 className={styles.sectionTitle}>Timeline</h2>
          <button className={styles.uploadBtn}>+ Upload</button>
        </div>

        {totalItems === 0 ? (
          <div className={styles.emptyTimeline}>
            <p className={styles.emptyText}>No items yet</p>
            <p className={styles.emptyHint}>
              Upload call recordings, chat screenshots, or status updates
            </p>
          </div>
        ) : (
          <div className={styles.emptyTimeline}>
            <p className={styles.emptyText}>
              {totalItems} items — timeline view coming soon
            </p>
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className={styles.overlay} onClick={() => setShowDeleteConfirm(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>Delete Space</h3>
            <p className={styles.modalText}>
              Are you sure you want to delete <strong>{space.name}</strong>? This
              will permanently remove all items within this space.
            </p>
            <div className={styles.modalActions}>
              <button
                className={styles.cancelBtn}
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </button>
              <button className={styles.confirmDeleteBtn} onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
