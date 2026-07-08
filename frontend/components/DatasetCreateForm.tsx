import { FormEvent, useState } from "react";
import SectionCard from "./SectionCard";

type DatasetCreateFormProps = {
  token: string | null;
  loading: boolean;
  onCreate: (payload: { name: string; description?: string | null }) => Promise<void>;
};

export default function DatasetCreateForm({ token, loading, onCreate }: DatasetCreateFormProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate({ name, description: description || null });
    setName("");
    setDescription("");
  }

  return (
    <SectionCard title="Create Dataset" description="Creates metadata only. Owner is taken from the authenticated user.">
      <form className="grid gap-3 md:grid-cols-[1fr_2fr_auto] md:items-end" onSubmit={submitForm}>
        <label className="field-label">Dataset name
          <input className="input-field" disabled={!token} required value={name} onChange={(event) => setName(event.target.value)} placeholder="Sales CSV" />
        </label>
        <label className="field-label">Description
          <input className="input-field" disabled={!token} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Optional note" />
        </label>
        <button className="btn-primary" disabled={!token || loading} type="submit">{loading ? "Creating..." : "Create"}</button>
      </form>
      {!token ? <p className="mt-3 text-sm text-amber-700">Log in before creating datasets.</p> : null}
    </SectionCard>
  );
}
