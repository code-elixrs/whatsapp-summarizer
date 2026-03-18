import { useNavigate } from "react-router-dom";
import type { Space } from "../../types/space";
import styles from "./SpaceCard.module.css";

interface SpaceCardProps {
  space: Space;
}

export function SpaceCard({ space }: SpaceCardProps) {
  const navigate = useNavigate();
  const initial = space.name.charAt(0).toUpperCase();
  const totalItems =
    space.item_counts.calls +
    space.item_counts.chats +
    space.item_counts.statuses +
    space.item_counts.media;

  const timeAgo = getTimeAgo(space.updated_at);

  return (
    <div className={styles.card} onClick={() => navigate(`/spaces/${space.id}`)}>
      <div className={styles.header}>
        <div className={styles.avatar} style={{ background: space.color }}>
          {initial}
        </div>
        <div className={styles.info}>
          <div className={styles.name}>{space.name}</div>
          <div className={styles.meta}>Updated {timeAgo}</div>
        </div>
      </div>
      {space.description && (
        <div className={styles.description}>{space.description}</div>
      )}
      <div className={styles.stats}>
        {space.item_counts.calls > 0 && (
          <StatBadge count={space.item_counts.calls} label="calls" />
        )}
        {space.item_counts.chats > 0 && (
          <StatBadge count={space.item_counts.chats} label="chats" />
        )}
        {space.item_counts.statuses > 0 && (
          <StatBadge count={space.item_counts.statuses} label="statuses" />
        )}
        {space.item_counts.media > 0 && (
          <StatBadge count={space.item_counts.media} label="media" />
        )}
        {totalItems === 0 && (
          <span className={styles.emptyStats}>No items yet</span>
        )}
      </div>
    </div>
  );
}

function StatBadge({ count, label }: { count: number; label: string }) {
  return (
    <span className={styles.stat}>
      <span className={styles.statCount}>{count}</span> {label}
    </span>
  );
}

function getTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}
