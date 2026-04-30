"use client";

/**
 * Client island that toggles every native <details> child of #faq-list.
 * Lives in its own file so the surrounding FAQ component stays a pure
 * server-rendered <details> tree (no hydration cost for the FAQ body
 * itself).
 */
export function FaqExpandAll() {
  return (
    <button
      type="button"
      onClick={() => {
        if (typeof document === "undefined") return;
        const items = document.querySelectorAll<HTMLDetailsElement>(
          "#faq-list > details",
        );
        const allOpen = Array.from(items).every((el) => el.open);
        items.forEach((el) => {
          el.open = !allOpen;
        });
      }}
      className="text-xs font-mono uppercase tracking-[0.16em] text-muted hover:text-ink transition shrink-0"
      aria-label="Expand or collapse all FAQ entries"
    >
      [ expand / collapse all ]
    </button>
  );
}
