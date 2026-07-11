"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import * as api from "@/lib/api";
import { storeToken } from "@/lib/auth";
import ErrorAlert from "@/components/mvp/ErrorAlert";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signedUp = searchParams.get("signed_up") === "1";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await api.login(email, password);
      storeToken(token.access_token);
      await api.getCurrentUser(token.access_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-slate-950 lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative flex min-h-[42vh] items-end overflow-hidden p-6 text-white sm:p-10 lg:min-h-screen">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,_#020617_0%,_#134e4a_56%,_#f59e0b_140%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_28rem)]" />
        <div className="absolute inset-x-8 top-8 h-px bg-white/20" />
        <div className="relative max-w-xl">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-300 text-sm font-black text-slate-950 shadow-lg">QS</span>
            <span className="text-lg font-bold">QueryShield AI</span>
          </div>
          <p className="mt-8 inline-flex rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-100 backdrop-blur">Secure analytics workspace</p>
          <h1 className="mt-4 text-4xl font-black tracking-normal sm:text-5xl">Governed analytics, from CSV to bounded BigQuery results.</h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-200">Phase-1 workspace for dataset onboarding, SQL generation, validation, dry runs, execution, and audit review.</p>
          <div className="mt-8 grid gap-3 text-sm sm:grid-cols-3">
            {[
              "Upload CSV",
              "Validate SQL",
              "Review audits",
            ].map((item) => <div className="rounded-2xl border border-white/15 bg-white/10 p-3 font-semibold text-white backdrop-blur" key={item}>{item}</div>)}
          </div>
        </div>
      </section>

      <section className="flex items-center justify-center bg-slate-50 px-4 py-8">
        <div className="app-surface w-full max-w-md p-7">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Secure workspace</p>
          <h2 className="mt-2 text-3xl font-black tracking-normal text-slate-950">Log in</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Access your governed analytics workflow with a polished, audit-ready experience.</p>
          {signedUp ? <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">Account created. Log in to continue.</div> : null}
          <div className="mt-4"><ErrorAlert message={error} /></div>
          <form className="mt-5 space-y-4" onSubmit={submit}>
            <label className="field-label">Email
              <input className="input-field" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label className="field-label">Password
              <input className="input-field" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <button className="btn-primary w-full" disabled={loading} type="submit">{loading ? "Logging in..." : "Login"}</button>
          </form>
          <p className="mt-5 text-sm text-slate-600">No account? <Link className="font-bold text-teal-700 hover:text-teal-900" href="/signup">Sign up</Link></p>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8"><section className="app-surface w-full max-w-md p-6 text-sm text-slate-700">Loading login...</section></main>}>
      <LoginContent />
    </Suspense>
  );
}