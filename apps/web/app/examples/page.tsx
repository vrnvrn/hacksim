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
          Pre-recorded simulations. Each run is reproducible with the prompt
          shown on the card. Click into any sim to watch the live page or
          jump to the showcase.
        </p>
        <div className="mt-12">
          <HeroExamples />
        </div>
      </main>
      <Footer />
    </>
  );
}
