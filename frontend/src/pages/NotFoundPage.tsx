import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div style={{ textAlign: "center", paddingTop: "120px" }}>
      <h1 style={{ fontSize: "48px", fontWeight: 700, marginBottom: "8px" }}>404</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Page not found
      </p>
      <Link to="/">Go home</Link>
    </div>
  );
}
