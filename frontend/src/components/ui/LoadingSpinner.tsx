import styles from "./LoadingSpinner.module.css";

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <div
      className={styles.spinner}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  );
}
