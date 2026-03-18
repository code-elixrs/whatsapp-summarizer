import styles from "./HomePage.module.css";

export function HomePage() {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Spaces</h1>
        <p className={styles.subtitle}>
          Organize your conversations and media by person
        </p>
      </div>
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>+</div>
        <p className={styles.emptyText}>No spaces yet</p>
        <p className={styles.emptyHint}>Create your first space to get started</p>
      </div>
    </div>
  );
}
