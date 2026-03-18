import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import styles from "./RootLayout.module.css";

export function RootLayout() {
  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
