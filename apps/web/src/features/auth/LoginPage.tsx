import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/apiClient";
import { ErrorState } from "@/components/ErrorState";

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Sign in</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Document Intelligence workspace access.</p>
      <form
        className="mt-8 space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr(null);
          try {
            await login(email, password);
            nav("/app");
          } catch (ex: unknown) {
            if (ex instanceof ApiError) {
              const b = ex.body as { error?: { message?: string } } | null;
              setErr(b?.error?.message ?? ex.message);
            } else {
              setErr(ex instanceof Error ? ex.message : "Login failed");
            }
          }
        }}
      >
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          Email
          <input
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            autoComplete="username"
            required
          />
        </label>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          Password
          <input
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        {err ? <ErrorState title="Could not sign in" detail={err} /> : null}
        <button
          type="submit"
          className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900"
        >
          Continue
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        No account?{" "}
        <Link className="font-medium text-slate-900 underline dark:text-white" to="/register">
          Register
        </Link>
      </p>
    </div>
  );
}
