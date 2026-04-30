import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { HeroExamples } from "@/components/HeroExamples";

export default function ExamplesPage() {
  return (
    <>
      <Nav />
      <main className="max-w-7xl mx-auto px-6 lg:px-8 pt-20 pb-24">
        <h1 className="font-display text-5xl lg:text-6xl font-semibold text-ink leading-tight">
          Example runs
        </h1>
        <p className="text-xl text-body mt-6 max-w-3xl leading-snug">
          Click any card to spin up a fresh sim with that prompt. Each run
          is non-deterministic, so the projects you get will not match the
          tile copy verbatim.
        </p>
        <div className="mt-12">
          <HeroExamples showHeader={false} />
        </div>
      </main>
      <Footer />
    </>
  );
}
