import Link from "next/link";

// Sticky top nav, 64px tall, white surface with a 1px bottom border. Logo
// wordmark on the left, three text links on the right. No login.
export function Nav() {
  return (
    <header
      className="sticky top-0 z-30 h-16 bg-surface border-b border-border"
      role="banner"
    >
      <nav
        aria-label="Primary"
        className="max-w-7xl mx-auto px-6 lg:px-8 h-full flex items-center justify-between"
      >
        <Link
          href="/"
          className="font-display font-semibold text-xl tracking-tight text-ink flex items-center gap-2"
          aria-label="HackSim home"
        >
          <span aria-hidden className="text-accent">◇</span>
          hacksim
        </Link>
        <ul className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm font-mono text-body uppercase tracking-wide">
          <li>
            <Link
              href="/examples"
              className="px-2 py-1 hover:text-ink transition"
            >
              [ examples ]
            </Link>
          </li>
          <li>
            <Link
              href="/docs"
              className="px-2 py-1 hover:text-ink transition"
            >
              [ docs ]
            </Link>
          </li>
          <li>
            <a
              href="https://github.com/gensyn-ai/axl"
              target="_blank"
              rel="noreferrer"
              className="px-2 py-1 hover:text-ink transition"
            >
              [ github ]
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
