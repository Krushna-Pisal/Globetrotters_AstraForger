import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Lock } from "lucide-react";
import { useAuth } from "./lib/auth";
import type { Role } from "./lib/api";
import { AppShell } from "./components/AppShell";
import { EmptyState } from "./components/ui";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import EngineerPage from "./pages/EngineerPage";
import OperationsPage from "./pages/OperationsPage";
import CfoPage from "./pages/CfoPage";
import BaselinePage from "./pages/BaselinePage";

function Protected({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { session, can } = useAuth();
  const loc = useLocation();
  if (!session) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  if (roles && !can(...roles)) {
    return (
      <AppShell title="Not part of your view">
        <div className="card">
          <EmptyState title="This view belongs to another role">
            Your lens is enforced on the server: the API would refuse this data for your token. Use the navigation to open
            your own view.
          </EmptyState>
          <div className="flex justify-center pb-8 text-ink-4">
            <Lock size={16} />
          </div>
        </div>
      </AppShell>
    );
  }
  return <>{children}</>;
}

function Home() {
  const { session } = useAuth();
  return <Navigate to={session ? session.home : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Home />} />
      <Route path="/overview" element={<Protected><OverviewPage /></Protected>} />
      <Route path="/engineer" element={<Protected roles={["engineer"]}><EngineerPage /></Protected>} />
      <Route path="/operations" element={<Protected roles={["operations"]}><OperationsPage /></Protected>} />
      <Route path="/cfo" element={<Protected roles={["cfo"]}><CfoPage /></Protected>} />
      <Route path="/baseline" element={<Protected roles={["cfo"]}><BaselinePage /></Protected>} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
