"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "online" | "offline";

export function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/healthz")
      .then((response) => {
        if (!cancelled) setStatus(response.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setStatus("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const label = {
    checking: "Checking API…",
    online: "API online",
    offline: "API offline",
  }[status];

  const color = {
    checking: "bg-slate-200 text-slate-700",
    online: "bg-emerald-100 text-emerald-800",
    offline: "bg-rose-100 text-rose-800",
  }[status];

  return <span className={`rounded-full px-3 py-1 text-sm font-medium ${color}`}>{label}</span>;
}
