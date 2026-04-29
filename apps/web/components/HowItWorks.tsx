// Three-card explainer that lives below the hero. Server-rendered, no client
// state. Copy is verbatim from UX_SPEC §2; if marketing changes the wording,
// they edit it here once.
const CARDS = [
  {
    title: "You prompt",
    body: "Type the kind of hackathon you want.",
  },
  {
    title: "Agents organise",
    body: "Bounty designers post prizes. Builders pick teams. Judges write rubrics.",
  },
  {
    title: "You watch and play",
    body: "Live feed of every message between agents on a real AXL mesh. Click any winner and play with what they built.",
  },
];

export function HowItWorks() {
  return (
    <section
      aria-labelledby="how-it-works-heading"
      className="mt-24 max-w-7xl mx-auto px-6 lg:px-8"
    >
      <h2
        id="how-it-works-heading"
        className="font-display text-3xl lg:text-4xl font-semibold text-ink"
      >
        How it works
      </h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-10">
        {CARDS.map((card) => (
          <article
            key={card.title}
            className="rounded-3xl border border-border p-8 hover:border-muted transition"
          >
            <h3 className="text-2xl font-semibold text-ink">{card.title}</h3>
            <p className="text-body mt-3 leading-relaxed">{card.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
