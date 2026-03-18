import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { SpaceCard } from "../components/spaces/SpaceCard";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { listSpaces } from "../lib/spaces";
import type { Space } from "../types/space";
import styles from "./HomePage.module.css";

export function HomePage() {
  const navigate = useNavigate();
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const fetchSpaces = useCallback(async (query?: string) => {
    try {
      setError(null);
      const data = await listSpaces(query || undefined);
      setSpaces(data.spaces);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load spaces");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSpaces();
  }, [fetchSpaces]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSpaces(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, fetchSpaces]);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Spaces</h1>
          <p className={styles.subtitle}>
            Organize your conversations and media by person
          </p>
        </div>
        <button
          className={styles.createBtn}
          onClick={() => navigate("/spaces/new")}
        >
          + New Space
        </button>
      </div>

      <div className={styles.searchBar}>
        <svg
          className={styles.searchIcon}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Search spaces..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading && (
        <div className={styles.centered}>
          <LoadingSpinner size={32} />
        </div>
      )}

      {error && (
        <div className={styles.error}>
          {error}
          <button onClick={() => fetchSpaces()} className={styles.retryBtn}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && spaces.length > 0 && (
        <div className={styles.grid}>
          {spaces.map((space) => (
            <SpaceCard key={space.id} space={space} />
          ))}
        </div>
      )}

      {!loading && !error && spaces.length === 0 && !search && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>+</div>
          <p className={styles.emptyText}>No spaces yet</p>
          <p className={styles.emptyHint}>
            Create your first space to get started
          </p>
          <button
            className={styles.createBtn}
            onClick={() => navigate("/spaces/new")}
            style={{ marginTop: "16px" }}
          >
            Create Space
          </button>
        </div>
      )}

      {!loading && !error && spaces.length === 0 && search && (
        <div className={styles.empty}>
          <p className={styles.emptyText}>No spaces match "{search}"</p>
        </div>
      )}
    </div>
  );
}
