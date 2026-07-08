import type { User } from "@/lib/types";
import SectionCard from "./SectionCard";

type CurrentUserSectionProps = {
  token: string | null;
  user: User | null;
  loading: boolean;
  onGetCurrentUser: () => void;
};

export default function CurrentUserSection({ token, user, loading, onGetCurrentUser }: CurrentUserSectionProps) {
  return (
    <SectionCard title="Current User" description="Calls the protected /users/me endpoint with the current bearer token.">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button className="btn-primary" disabled={!token || loading} onClick={onGetCurrentUser} type="button">
          {loading ? "Loading user..." : "Get Current User"}
        </button>
        {!token ? <span className="text-sm text-amber-700">No valid token is available.</span> : null}
      </div>
      {user ? (
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
          <div><dt className="meta-label">ID</dt><dd className="meta-value">{user.id}</dd></div>
          <div><dt className="meta-label">Email</dt><dd className="meta-value break-all">{user.email}</dd></div>
          <div><dt className="meta-label">Full name</dt><dd className="meta-value">{user.full_name || "-"}</dd></div>
          <div><dt className="meta-label">Active</dt><dd className="meta-value">{String(user.is_active)}</dd></div>
          <div><dt className="meta-label">Superuser</dt><dd className="meta-value">{String(user.is_superuser)}</dd></div>
        </dl>
      ) : (
        <p className="text-sm text-slate-600">No current user loaded.</p>
      )}
    </SectionCard>
  );
}
