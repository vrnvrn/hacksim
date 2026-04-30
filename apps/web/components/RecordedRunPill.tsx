/**
 * RecordedRunPill. On the hosted Vercel preview, every "live" page is a
 * fixture replay. This pill surfaces the date the run was recorded so a
 * visitor reading /sim/[id] cannot mistake the snapshot for a live mesh.
 *
 * Renders only when NEXT_PUBLIC_HOSTED_PREVIEW=true and
 * NEXT_PUBLIC_USE_MOCKS=true. Compiles out for local dev and for any
 * future Mode V2 deploy with mocks off.
 */

const HOSTED = process.env.NEXT_PUBLIC_HOSTED_PREVIEW === "true";
const MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function RecordedRunPill({ createdAt }: { createdAt: string }) {
  if (!HOSTED || !MOCKS) return null;
  const date = formatDate(createdAt);
  return (
    <span
      role="status"
      aria-label={`Recorded run from ${date}`}
      className="inline-flex items-center gap-2 rounded-full border border-border bg-canvas px-3 py-1 text-xs font-mono uppercase tracking-[0.14em] text-muted"
    >
      <span aria-hidden="true">[ recorded {date} ]</span>
    </span>
  );
}

function formatDate(iso: string): string {
  // Trim to YYYY-MM-DD without locale-dependent parsing so SSR and
  // client agree on the rendered string.
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(iso);
  return m ? m[1] : iso;
}
