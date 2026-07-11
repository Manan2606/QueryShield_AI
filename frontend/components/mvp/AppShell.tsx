"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";
import * as api from "@/lib/api";
import { clearStoredToken, getStoredToken } from "@/lib/auth";
import type { User } from "@/lib/types";

const navItems = [
  { href: "/dashboard", label: "Dashboard", marker: "01" },
  { href: "/datasets", label: "Datasets", marker: "02" },
  { href: "/queries/new", label: "Ask Query", marker: "03" },
  { href: "/history", label: "Query History", marker: "04" },
  { href: "/audit-logs", label: "Audit Logs", marker: "05" },
];

type AppShellProps = {
  title: string;
  children: (context: { token: string; user: User }) => ReactNode;
};

export default function AppShell({ title, children }: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      router.replace("/login");
      return;
    }

    setToken(storedToken);
    api.getCurrentUser(storedToken)
      .then((currentUser) => {
        setUser(currentUser);
        setError(null);
      })
      .catch(() => {
        clearStoredToken();
        setToken(null);
        setUser(null);
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  const initials = useMemo(() => {
    const label = user?.full_name || user?.email || "U";
    return label.slice(0, 2).toUpperCase();
  }, [user]);

  function logout() {
    clearStoredToken();
    router.replace("/login");
  }

  if (loading || !token || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_left,_rgba(20,184,166,0.16),_transparent_24rem)] p-6">
        <div className="app-surface w-full max-w-md p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-sm font-black text-white shadow-lg">QS</div>
          <p className="mt-5 text-sm font-semibold uppercase tracking-[0.22em] text-teal-700">Secure workspace</p>
          <p className="mt-2 text-lg font-semibold text-slate-900">Validating your QueryShield session</p>
          <p className="mt-2 text-sm text-slate-500">We are checking your active backend connection.</p>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen text-slate-950">
      <aside className="fixed inset-y-0 left-0 hidden w-72 bg-[linear-gradient(180deg,_#020617_0%,_#111827_100%)] text-white shadow-[0_24px_80px_rgba(2,6,23,0.35)] lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-white/10 p-6">
            <Link className="flex items-center gap-3" href="/dashboard">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-300 text-sm font-black text-slate-950 shadow-lg">QS</span>
              <span>
                <span className="block text-lg font-bold tracking-normal">QueryShield AI</span>
                <span className="block text-xs font-medium text-slate-400">Governed analytics</span>
              </span>
            </Link>
          </div>

          <nav className="flex-1 space-y-1 p-3">
            {navItems.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`) || (item.href === "/datasets" && pathname.startsWith("/datasets/"));
              return (
                <Link className={`group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${active ? "bg-white text-slate-950 shadow-lg" : "text-slate-300 hover:bg-white/10 hover:text-white"}`} href={item.href} key={item.href}>
                  <span className={`flex h-7 w-8 items-center justify-center rounded-xl border text-[11px] font-bold ${active ? "border-teal-200 bg-teal-50 text-teal-800" : "border-white/10 bg-white/5 text-slate-400 group-hover:text-white"}`}>{item.marker}</span>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="m-3 rounded-2xl border border-white/10 bg-white/10 p-4 shadow-inner">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-200">Phase 1 MVP</p>
            <p className="mt-2 text-sm leading-6 text-slate-300">Upload CSV data, generate governed SQL, validate cost, execute bounded results, and review audit history.</p>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
          <div className="flex min-h-20 flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">QueryShield AI</p>
              <h1 className="mt-1 text-2xl font-black tracking-normal text-slate-950">{title}</h1>
              <div className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:hidden">
                {navItems.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return <Link className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-bold ${active ? "border-teal-300 bg-teal-50 text-teal-800" : "border-slate-200 bg-white text-slate-700"}`} href={item.href} key={item.href}>{item.label}</Link>;
                })}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden rounded-2xl border border-slate-200 bg-white px-3 py-2 text-right shadow-sm sm:block">
                <p className="text-sm font-bold text-slate-900">{user.full_name || user.email}</p>
                <p className="text-xs font-semibold text-teal-700">Backend session active</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-sm font-black text-white shadow-sm">{initials}</div>
              <button className="btn-secondary" onClick={logout} type="button">Logout</button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
          {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800 shadow-sm">{error}</div> : null}
          {children({ token, user })}
        </main>
      </div>
    </div>
  );
}