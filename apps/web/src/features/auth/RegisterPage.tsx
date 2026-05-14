import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/apiClient";
import { ErrorState } from "@/components/ErrorState";

export function RegisterPage() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [err, setErr] = useState<string | null>(null);

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Create account</h1>
      <form
        className="mt-8 space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr(null);
          try {
            await register(email, password, fullName || undefined);
            nav("/app");
          } catch (ex: unknown) {
            if (ex instanceof ApiError) {
              const b = ex.body as { error?: { message?: string } } | null;
              setErr(b?.error?.message ?? ex.message);
            } else {
              setErr(ex instanceof Error ? ex.message : "Registration failed");
            }
          }
        }}
      >
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          Full name (optional)
          <input
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          Email
          <input
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </label>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          Password (min 8 characters)
          <input
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            minLength={8}
            required
          />
        </label>
        {err ? <ErrorState title="Could not register" detail={err} /> : null}
        <button
          type="submit"
          className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900"
        >
          Create workspace access
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        Already have an account?{" "}
        <Link className="font-medium text-slate-900 underline dark:text-white" to="/login">
          Sign in
        </Link>
      </p>
    </div>
  );
}
