"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import * as api from "@/lib/api";
import ErrorAlert from "@/components/mvp/ErrorAlert";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords must match.");
      return;
    }
    setLoading(true);
    try {
      await api.signup({ email, password, full_name: fullName || null });
      router.replace("/login?signed_up=1");
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-slate-950 lg:grid-cols-[0.95fr_1.05fr]">
      <section className="flex items-center justify-center bg-slate-50 px-4 py-8 lg:order-1">
        <div className="app-surface w-full max-w-md p-7">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Create workspace access</p>
          <h1 className="mt-2 text-3xl font-black tracking-normal text-slate-950">Sign up</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">Launch your Phase-1 QueryShield account and begin shaping governed questions.</p>
          <div className="mt-4"><ErrorAlert message={error} /></div>
          <form className="mt-5 space-y-4" onSubmit={submit}>
            <label className="field-label">Full name
              <input className="input-field" required value={fullName} onChange={(event) => setFullName(event.target.value)} />
            </label>
            <label className="field-label">Email
              <input className="input-field" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label className="field-label">Password
              <input className="input-field" required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <label className="field-label">Confirm password
              <input className="input-field" required minLength={8} type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
            </label>
            <button className="btn-primary w-full" disabled={loading} type="submit">{loading ? "Creating account..." : "Create account"}</button>
          </form>
          <p className="mt-5 text-sm text-slate-600">Already have an account? <Link className="font-bold text-teal-700 hover:text-teal-900" href="/login">Log in</Link></p>
        </div>
      </section>

      <section className="relative flex min-h-[36vh] items-end overflow-hidden p-6 text-white sm:p-10 lg:order-2 lg:min-h-screen">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,_#020617_0%,_#115e59_60%,_#f59e0b_145%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_28rem)]" />
        <div className="relative max-w-xl">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-300 text-sm font-black text-slate-950 shadow-lg">QS</span>
            <span className="text-lg font-bold">QueryShield AI</span>
          </div>
          <p className="mt-8 inline-flex rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-100 backdrop-blur">Control plane for safe data questions</p>
          <h2 className="mt-4 text-4xl font-black tracking-normal sm:text-5xl">A clean control plane for safe data questions.</h2>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-200">Every generated query moves through validation, cost checks, bounded execution, history, and auditability.</p>
        </div>
      </section>
    </main>
  );
}