"use client";

import { useEffect, useState } from "react";

type MeResponse = {
  user: {
    login: string;
    is_admin: boolean;
  };
  csrf_token: string;
};

type SessionState = "loading" | "signed-out" | "signed-in" | "error";

export function SessionPanel() {
  const [session, setSession] = useState<MeResponse | null>(null);
  const [state, setState] = useState<SessionState>("loading");

  useEffect(() => {
    let cancelled = false;

    fetch("/api/v1/me", { credentials: "same-origin" })
      .then(async (response) => {
        if (cancelled) return;
        if (response.status === 401) {
          setState("signed-out");
          return;
        }
        if (!response.ok) {
          setState("error");
          return;
        }
        const body = (await response.json()) as MeResponse;
        if (!cancelled) {
          setSession(body);
          setState("signed-in");
        }
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function signOut() {
    if (!session) return;
    try {
      const response = await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": session.csrf_token },
        credentials: "same-origin",
      });
      if (response.ok) {
        setSession(null);
        setState("signed-out");
      }
    } catch {
      setState("error");
    }
  }

  if (state === "loading") {
    return <span className="text-sm text-slate-500">Checking session…</span>;
  }

  if (state === "error") {
    return <span className="text-sm text-rose-700">Session unavailable</span>;
  }

  if (state === "signed-out" || !session) {
    return (
      <a
        className="rounded-full bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        href="/api/v1/auth/github/login"
      >
        Sign in with GitHub
      </a>
    );
  }

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-slate-600">
        Signed in as <strong className="text-slate-900">{session.user.login}</strong>
      </span>
      <button
        className="rounded-full border border-slate-300 px-3 py-1 font-medium text-slate-700 hover:bg-slate-100"
        onClick={signOut}
        type="button"
      >
        Sign out
      </button>
    </div>
  );
}
