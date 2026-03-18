import { Link } from "react-router-dom";
import styles from "./Navbar.module.css";

export function Navbar() {
  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <Link to="/" className={styles.logo}>
          <span className={styles.logoIcon}>L</span>
          <span className={styles.logoText}>LifeLog</span>
        </Link>
      </div>
    </nav>
  );
}
