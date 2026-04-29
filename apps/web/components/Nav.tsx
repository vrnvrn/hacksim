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
          className="font-display font-semibold text-xl tracking-tight text-ink"
          aria-label="HackSim home"
        >
          HackSim
        </Link>
        <ul className="flex items-center gap-8 text-sm font-medium text-body">
          <li>
            <Link href="/examples" className="hover:opacity-60 transition">
              Examples
            </Link>
          </li>
          <li>
            <Link href="/docs" className="hover:opacity-60 transition">
              Docs
            </Link>
          </li>
          <li>
            <a
              href="https://github.com/gensyn-ai/axl"
              target="_blank"
              rel="noreferrer"
              className="hover:opacity-60 transition"
            >
              GitHub
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
