import { type ReactElement, useEffect } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AppShell } from "@/layouts/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { DocumentsPage } from "@/features/documents/DocumentsPage";
import { DocumentUploadPage } from "@/features/documents/DocumentUploadPage";
import { DocumentDetailPage } from "@/features/documents/DocumentDetailPage";
import { QueryChatPage } from "@/features/query/QueryChatPage";
import { SessionsListPage } from "@/features/sessions/SessionsListPage";
import { SessionDetailPage } from "@/features/sessions/SessionDetailPage";
import { DiagnosticsPage } from "@/features/diagnostics/DiagnosticsPage";
import { WorkspaceHomePage } from "@/pages/WorkspaceHomePage";
import { WorkspaceIndexRedirect } from "@/routes/WorkspaceIndexRedirect";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) {
    return (
      <div className="p-8">
        <LoadingSkeleton className="h-12 w-48" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  return children;
}

function ThemeInit() {
  useEffect(() => {
    const t = localStorage.getItem("docintel_theme");
    if (t === "dark") document.documentElement.classList.add("dark");
  }, []);
  return null;
}

export function AppRoutes() {
  return (
    <AuthProvider>
      <ThemeInit />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/app"
          element={
            <RequireAuth>
              <Outlet />
            </RequireAuth>
          }
        >
          <Route index element={<WorkspaceHomePage />} />
          <Route path="workspace/:workspaceId" element={<AppShell />}>
            <Route index element={<WorkspaceIndexRedirect />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="documents/upload" element={<DocumentUploadPage />} />
            <Route path="documents/:documentId" element={<DocumentDetailPage />} />
            <Route path="query" element={<QueryChatPage />} />
            <Route path="sessions" element={<SessionsListPage />} />
            <Route path="sessions/:sessionId" element={<SessionDetailPage />} />
            <Route path="diagnostics" element={<DiagnosticsPage />} />
          </Route>
        </Route>
        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </AuthProvider>
  );
}
