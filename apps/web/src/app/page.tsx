import { ApiStatus } from "@/components/ApiStatus";
import { SessionPanel } from "@/components/SessionPanel";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
      <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-500">
        Community LLM
      </p>
      <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
        A community-owned small-model lab and inference co-op.
      </h1>
      <p className="mt-6 text-lg leading-8 text-slate-600">
        Contribute GPU time, run evaluation or LoRA jobs, earn best-effort points, and use them for
        inference on models the community helps build.
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <ApiStatus />
        <SessionPanel />
        <a className="text-sm font-medium text-slate-700 underline" href="/api/docs">
          API docs
        </a>
      </div>
    </main>
  );
}
