import { FormEvent, useState } from "react";
import type { User } from "@/lib/types";
import SectionCard from "./SectionCard";

type AuthSectionProps = {
  token: string | null;
  currentUser: User | null;
  loading: string | null;
  onSignup: (payload: { full_name: string; email: string; password: string }) => Promise<void>;
  onLogin: (email: string, password: string) => Promise<void>;
  onLogout: () => void;
};

export default function AuthSection({ token, currentUser, loading, onSignup, onLogin, onLogout }: AuthSectionProps) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [signupFullName, setSignupFullName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  async function submitSignup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSignup({ full_name: signupFullName, email: signupEmail, password: signupPassword });
    setSignupPassword("");
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onLogin(loginEmail, loginPassword);
    setLoginPassword("");
  }

  return (
    <SectionCard title="Authentication" description="Signup returns a user record; login returns a bearer token stored in sessionStorage for this session.">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-1">
          <button className={`tab-button ${mode === "login" ? "tab-button-active" : ""}`} onClick={() => setMode("login")} type="button">Login</button>
          <button className={`tab-button ${mode === "signup" ? "tab-button-active" : ""}`} onClick={() => setMode("signup")} type="button">Signup</button>
        </div>
        {token ? <span className="status-badge bg-emerald-100 text-emerald-800">Token stored</span> : <span className="status-badge bg-slate-100 text-slate-700">No token</span>}
        {currentUser ? <span className="text-sm text-slate-600">Signed in as {currentUser.email}</span> : null}
        <button className="btn-secondary ml-auto" disabled={!token} onClick={onLogout} type="button">Logout</button>
      </div>

      {mode === "signup" ? (
        <form className="grid gap-3 md:grid-cols-3" onSubmit={submitSignup}>
          <label className="field-label">Full name
            <input className="input-field" value={signupFullName} onChange={(event) => setSignupFullName(event.target.value)} placeholder="Test User" />
          </label>
          <label className="field-label">Email
            <input className="input-field" required type="email" value={signupEmail} onChange={(event) => setSignupEmail(event.target.value)} placeholder="user@example.com" />
          </label>
          <label className="field-label">Password
            <input className="input-field" required type="password" value={signupPassword} onChange={(event) => setSignupPassword(event.target.value)} placeholder="Password" />
          </label>
          <div className="md:col-span-3">
            <button className="btn-primary" disabled={loading === "signup"} type="submit">{loading === "signup" ? "Signing up..." : "Sign up"}</button>
          </div>
        </form>
      ) : (
        <form className="grid gap-3 md:grid-cols-2" onSubmit={submitLogin}>
          <label className="field-label">Email
            <input className="input-field" required type="email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} placeholder="user@example.com" />
          </label>
          <label className="field-label">Password
            <input className="input-field" required type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} placeholder="Password" />
          </label>
          <div className="md:col-span-2">
            <button className="btn-primary" disabled={loading === "login"} type="submit">{loading === "login" ? "Logging in..." : "Log in"}</button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}
