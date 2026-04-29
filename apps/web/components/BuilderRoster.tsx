import type { Builder } from "@/lib/types";
import { BuilderChip } from "./BuilderChip";

export function BuilderRoster({ builders }: { builders: Builder[] }) {
  if (builders.length === 0) {
    return (
      <p className="text-sm text-muted">
        No builders connected yet. The mesh is still bootstrapping.
      </p>
    );
  }
  return (
    <div
      role="list"
      aria-label="Builders"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
    >
      {builders.map((b) => (
        <div role="listitem" key={b.peer_id}>
          <BuilderChip builder={b} />
        </div>
      ))}
    </div>
  );
}
