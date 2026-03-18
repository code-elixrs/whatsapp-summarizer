import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSpace } from "../lib/spaces";
import styles from "./CreateSpacePage.module.css";

const COLORS = [
  "#7c3aed", "#3b82f6", "#10b981", "#f59e0b",
  "#ef4444", "#ec4899", "#8b5cf6", "#06b6d4",
];

export function CreateSpacePage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initial = name.charAt(0).toUpperCase() || "?";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const space = await createSpace({
        name: name.trim(),
        description: description.trim() || undefined,
        color,
      });
      navigate(`/spaces/${space.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create space");
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backBtn} onClick={() => navigate("/")}>
          &larr; Back
        </button>
        <h1 className={styles.title}>Create New Space</h1>
        <p className={styles.subtitle}>
          A space is a container for all media & conversations related to one
          person or context.
        </p>
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.avatarSection}>
          <div className={styles.avatarPreview} style={{ background: color }}>
            {initial}
          </div>
          <div className={styles.colorPicker}>
            <label className={styles.label}>Avatar color</label>
            <div className={styles.colors}>
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`${styles.colorOption} ${c === color ? styles.colorActive : ""}`}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                  aria-label={`Select color ${c}`}
                />
              ))}
            </div>
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="name">
            Name <span className={styles.required}>*</span>
          </label>
          <input
            id="name"
            className={styles.input}
            type="text"
            placeholder="e.g., Rahul Sharma"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={255}
            autoFocus
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="description">
            Description
          </label>
          <textarea
            id="description"
            className={styles.textarea}
            placeholder="Any notes about this space..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.cancelBtn}
            onClick={() => navigate("/")}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!name.trim() || submitting}
          >
            {submitting ? "Creating..." : "Create Space"}
          </button>
        </div>
      </form>
    </div>
  );
}
