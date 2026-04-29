import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { HeroPrompt } from "@/components/HeroPrompt";
import { HowItWorks } from "@/components/HowItWorks";
import { HeroExamplesAside } from "@/components/HeroExamplesAside";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main id="main">
        {/* Hero: above-the-fold, two columns. Left is the prompt, right is
            click-to-spin example presets. The whole thing fits inside one
            viewport on a 1440x900 laptop. */}
        <section
          className="max-w-7xl mx-auto px-6 lg:px-8 pt-10 lg:pt-12 pb-12"
          aria-labelledby="hero-heading"
        >
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_22rem] xl:grid-cols-[1fr_24rem] gap-10 lg:gap-12 items-start">
            <div>
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-accent">
                [ hacksim ]
              </p>
              <h1
                id="hero-heading"
                className="font-display font-semibold text-ink text-4xl md:text-5xl lg:text-6xl leading-[1.02] tracking-tight mt-3"
              >
                Run your own hackathon with agents.
              </h1>
              <p className="text-base lg:text-lg text-body mt-4 max-w-2xl leading-relaxed">
                Type one prompt. Autonomous agents on a Gensyn AXL mesh design
                the bounties, form teams, write real code, score submissions,
                and crown the winners. Watch it happen, then click any winner
                and play with what they built.
              </p>
              <HeroPrompt />
            </div>
            <HeroExamplesAside />
          </div>
        </section>

        <HowItWorks />
      </main>
      <Footer />
    </>
  );
}
