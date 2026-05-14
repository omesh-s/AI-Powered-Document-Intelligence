import { useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "@/context/AuthContext";

const linkCls =
  "block rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800";

const activeCls = "bg-slate-200 text-slate-900 dark:bg-slate-800 dark:text-white";

function NavItems({
  base,
  onNavigate,
}: {
  base: string;
  onNavigate?: () => void;
}) {
  return (
    <>
      <NavLink
        end
        to={`${base}/dashboard`}
        onClick={onNavigate}
        className={({ isActive }) => `${linkCls} ${isActive ? activeCls : ""}`}
      >
        Dashboard
      </NavLink>
      <NavLink
        to={`${base}/documents`}
        onClick={onNavigate}
        className={({ isActive }) => `${linkCls} ${isActive ? activeCls : ""}`}
      >
        Documents
      </NavLink>
      <NavLink
        to={`${base}/query`}
        onClick={onNavigate}
        className={({ isActive }) => `${linkCls} ${isActive ? activeCls : ""}`}
      >
        Query
      </NavLink>
      <NavLink
        to={`${base}/sessions`}
        onClick={onNavigate}
        className={({ isActive }) => `${linkCls} ${isActive ? activeCls : ""}`}
      >
        Sessions
      </NavLink>
      <NavLink
        to={`${base}/diagnostics`}
        onClick={onNavigate}
        className={({ isActive }) => `${linkCls} ${isActive ? activeCls : ""}`}
      >
        Diagnostics
      </NavLink>
    </>
  );
}

export function AppShell() {
  const { workspaceId } = useParams();
  const { logout, user } = useAuth();
  const nav = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const base = `/app/workspace/${workspaceId}`;

  if (!workspaceId) {
    nav("/app");
    return null;
  }

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:block">
        <div className="border-b border-slate-200 px-4 py-4 dark:border-slate-800">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Document Intelligence</div>
          <div className="mt-1 truncate text-sm text-slate-800 dark:text-slate-100">{user?.email}</div>
        </div>
        <nav className="space-y-1 p-3">
          <NavItems base={base} />
        </nav>
        <div className="space-y-2 p-3">
          <button
            type="button"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => {
              const el = document.documentElement;
              el.classList.toggle("dark");
              localStorage.setItem("docintel_theme", el.classList.contains("dark") ? "dark" : "light");
            }}
          >
            Toggle dark mode
          </button>
          <button
            type="button"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => {
              logout();
              nav("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          aria-label="Close menu"
          onClick={closeMobile}
        />
      ) : null}

      <div
        className={`fixed inset-y-0 left-0 z-50 w-56 transform border-r border-slate-200 bg-white shadow-lg transition-transform dark:border-slate-800 dark:bg-slate-900 md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-slate-200 px-4 py-4 dark:border-slate-800">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Document Intelligence</div>
          <div className="mt-1 truncate text-sm text-slate-800 dark:text-slate-100">{user?.email}</div>
        </div>
        <nav className="space-y-1 p-3">
          <NavItems base={base} onNavigate={closeMobile} />
        </nav>
        <div className="space-y-2 p-3">
          <button
            type="button"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => {
              const el = document.documentElement;
              el.classList.toggle("dark");
              localStorage.setItem("docintel_theme", el.classList.contains("dark") ? "dark" : "light");
            }}
          >
            Toggle dark mode
          </button>
          <button
            type="button"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => {
              logout();
              nav("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 md:hidden">
          <span className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">Workspace</span>
          <button
            type="button"
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-800 dark:border-slate-600 dark:text-slate-100"
            onClick={() => setMobileOpen((o) => !o)}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? "Close" : "Menu"}
          </button>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
