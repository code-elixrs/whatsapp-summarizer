import { Routes, Route } from "react-router-dom";
import { RootLayout } from "./components/layout/RootLayout";
import { HomePage } from "./pages/HomePage";
import { CreateSpacePage } from "./pages/CreateSpacePage";
import { SpaceDetailPage } from "./pages/SpaceDetailPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export function App() {
  return (
    <Routes>
      <Route element={<RootLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/spaces/new" element={<CreateSpacePage />} />
        <Route path="/spaces/:spaceId" element={<SpaceDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
