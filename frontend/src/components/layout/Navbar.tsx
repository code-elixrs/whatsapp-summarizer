import { useState, useCallback, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { SearchResultItem } from "../../types/media";
import { globalSearch } from "../../lib/media";
import styles from "./Navbar.module.css";

const RESULT_TYPE_LABELS: Record<string, string> = {
  chat_message: "Chat",
  transcript: "Transcript",
  media_item: "Item",
};

export function Navbar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setShowDropdown(false);
      return;
    }
    setLoading(true);
    try {
      const data = await globalSearch(q, 10);
      setResults(data.results);
      setShowDropdown(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => search(query), 300);
    return () => clearTimeout(timer);
  }, [query, search]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleResultClick(result: SearchResultItem) {
    setShowDropdown(false);
    setQuery("");
    navigate(`/spaces/${result.space_id}`);
  }

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <Link to="/" className={styles.logo}>
          <span className={styles.logoIcon}>L</span>
          <span className={styles.logoText}>LifeLog</span>
        </Link>

        <div className={styles.searchWrapper} ref={dropdownRef}>
          <svg
            className={styles.searchIcon}
            width="14"
            height="14"
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
            placeholder="Search everything..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => results.length > 0 && setShowDropdown(true)}
          />
          {loading && <span className={styles.searchSpinner} />}

          {showDropdown && results.length > 0 && (
            <div className={styles.dropdown}>
              {results.map((r, i) => (
                <button
                  key={`${r.result_type}-${r.item_id}-${i}`}
                  className={styles.dropdownItem}
                  onClick={() => handleResultClick(r)}
                >
                  <span className={styles.resultType}>
                    {RESULT_TYPE_LABELS[r.result_type] || r.result_type}
                  </span>
                  <span className={styles.resultSnippet}>{r.snippet}</span>
                  <span className={styles.resultSpace}>{r.space_name}</span>
                </button>
              ))}
            </div>
          )}

          {showDropdown && results.length === 0 && query.length >= 2 && !loading && (
            <div className={styles.dropdown}>
              <div className={styles.noResults}>No results for &ldquo;{query}&rdquo;</div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
