"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getStoredToken } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getStoredToken() ? "/dashboard" : "/login");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_left,_rgba(20,184,166,0.16),_transparent_24rem)] p-6">
      <div className="app-surface w-full max-w-md p-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-sm font-black text-white shadow-lg">QS</div>
        <p className="mt-5 text-sm font-semibold uppercase tracking-[0.2em] text-teal-700">Launching workspace</p>
        <h1 className="mt-2 text-xl font-black text-slate-950">Opening QueryShield AI</h1>
        <p className="mt-2 text-sm text-slate-600">Redirecting you to the right place for your governed analytics flow.</p>
      </div>
    </main>
  );
}
