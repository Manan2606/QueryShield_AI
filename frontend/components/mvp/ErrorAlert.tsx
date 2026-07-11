export default function ErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm font-semibold text-rose-800 shadow-sm">{message}</div>;
}