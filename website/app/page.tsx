import Header from '@/components/Header'
import Footer from '@/components/Footer'
import Hero from '@/components/Hero'
import Section from '@/components/Section'
import FeatureCard from '@/components/FeatureCard'
import StepCard from '@/components/StepCard'
import CodeBlock from '@/components/CodeBlock'
import Button from '@/components/Button'

export default function Home() {
  return (
    <>
      <Header />

      <main>
        {/* Hero Section */}
        <Hero />

        {/* Why Vidurai Exists */}
        <Section className="bg-bg-deep">
          <div className="text-center max-w-4xl mx-auto">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-8 sm:mb-12 text-balance">
              AI is powerful. Humans are brilliant.{' '}
              <span className="text-vidurai-purple">The bridge between them is broken.</span>
            </h2>

            <div className="text-left space-y-6 text-base sm:text-lg lg:text-xl text-slate-400 leading-relaxed">
              <p>Humans over-explain.<br />AIs hallucinate.<br />Context gets scattered across terminals, files, logs, and browsers.</p>

              <p className="pt-4">Every time you ask an AI for help, you repeat the same explanations:</p>

              <ul className="space-y-3 pl-6 list-disc list-inside">
                <li>What you just ran in your terminal</li>
                <li>Which file you just changed</li>
                <li>When the error started</li>
                <li>What environment you're in</li>
              </ul>

              <p className="pt-6 text-xl sm:text-2xl text-white font-semibold">
                Vidurai doesn't just store everything.
              </p>

              <p className="text-vidurai-purple text-lg sm:text-xl font-medium">
                It understands what matters — and forgets what doesn't.
              </p>
            </div>
          </div>
        </Section>

        {/* What Vidurai Does */}
        <Section className="bg-black">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-12 sm:mb-16 text-center">
            What Vidurai actually does
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
            <StepCard number="1" title="Watches your real work (locally)">
              <p className="mb-4">Vidurai quietly observes:</p>
              <ul className="space-y-2 list-disc list-inside">
                <li>File changes</li>
                <li>Terminal commands and outputs</li>
                <li>Project structure</li>
                <li>Error patterns</li>
              </ul>
              <p className="mt-4 text-slate-300">
                Everything stays on your machine. No uploads. No tracking. No cloud.
              </p>
            </StepCard>

            <StepCard number="2" title="Understands what matters">
              <p className="mb-4">Vidurai doesn't dump data into the AI. It analyzes:</p>
              <ul className="space-y-2 list-disc list-inside">
                <li>Which changes triggered errors</li>
                <li>Which files are actually relevant</li>
                <li>What your recent commands suggest you're trying to do</li>
                <li>Your emotional state: panic, confusion, flow</li>
              </ul>
            </StepCard>

            <StepCard number="3" title="Forgets strategically (विस्मृति engine)">
              <p className="mb-4">Vidurai applies strategic forgetting:</p>
              <ul className="space-y-2 list-disc list-inside">
                <li>Compresses redundant history (36.6% average reduction)</li>
                <li>Drops irrelevant logs and noise</li>
                <li>Keeps only the sharpest, highest-signal insights</li>
              </ul>
            </StepCard>

            <StepCard number="4" title="Whispers to any AI">
              <p className="mb-4">
                Press <kbd className="px-2 py-1 bg-slate-700 rounded text-sm">Ctrl+Shift+V</kbd> → Vidurai prepares context.<br />
                Press <kbd className="px-2 py-1 bg-slate-700 rounded text-sm">Ctrl+V</kbd> → the AI receives a natural-language summary like:
              </p>
              <CodeBlock>
                "The backend started failing right after you switched from Node 18 to Node 20. The last 4 commands were: npm install → npm run build → npm run start → ./migrate.sh. The failing file is server/database/client.js on line 42."
              </CodeBlock>
              <p className="mt-4 text-slate-300">
                Not 300 lines of logs. Just the truth.
              </p>
            </StepCard>
          </div>
        </Section>

        {/* Architecture */}
        <Section className="bg-bg-soft">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-12 text-center">
            How Vidurai sits between you and AI
          </h2>

          <div className="max-w-3xl mx-auto">
            <CodeBlock>
{`Your Activity
├─ Files
├─ Terminal
└─ Browser
     ↓
Vidurai Daemon (localhost:7777)
├─ Smart File Watcher
├─ Terminal Monitor
└─ Emotional & Intent Engine
     ↓
Intelligence Layer
├─ Strategic Forgetting (विस्मृति)
├─ Natural Language Mediation
└─ Pattern Recognition
     ↓
Browser Extension
Ctrl+Shift+V → Context Ready
Ctrl+V → AI Receives Insight`}
            </CodeBlock>

            <p className="mt-8 text-center text-lg sm:text-xl text-slate-400">
              <span className="text-vidurai-purple font-semibold">Human → Vidurai → AI</span>
              <br />
              A clean, intelligent chain of understanding.
            </p>
          </div>
        </Section>

        {/* Why Vidurai is Different */}
        <Section className="bg-black">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-12 text-center">
            Not a note app. Not a logger.{' '}
            <span className="text-vidurai-purple">A mediator.</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 sm:gap-12 max-w-5xl mx-auto">
            <div className="bg-red-950/20 border border-red-900/50 rounded-xl p-6 sm:p-8">
              <h3 className="text-2xl font-bold mb-6 text-red-400">Other tools</h3>
              <ul className="space-y-4 text-slate-400">
                <li>"Here are 500 lines of logs."</li>
                <li>"Here is your entire terminal history."</li>
                <li>"Here is everything in your project."</li>
              </ul>
            </div>

            <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-xl p-6 sm:p-8">
              <h3 className="text-2xl font-bold mb-6 text-emerald-400">Vidurai</h3>
              <ul className="space-y-4 text-slate-400">
                <li>"The crash started after your last migration."</li>
                <li>"The failing file is migrations/2024_10_final.sql."</li>
                <li>"The last config change was DB_HOST from localhost to db.internal."</li>
              </ul>
            </div>
          </div>

          <p className="mt-12 text-center text-xl sm:text-2xl text-slate-300 max-w-3xl mx-auto">
            Others try to remember everything.<br />
            <span className="text-vidurai-purple font-semibold">
              Vidurai chooses what to <em>forget</em> — so the AI gets only what it needs.
            </span>
          </p>
        </Section>

        {/* Features */}
        <Section className="bg-bg-deep">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-12 sm:mb-16 text-center">
            Features built for real developers
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
            <FeatureCard title="Intelligent context" icon="🧠">
              Vidurai correlates commands, errors, and file changes into meaningful stories instead of raw dumps.
            </FeatureCard>

            <FeatureCard title="Emotional awareness" icon="💭">
              Detects frustration, confusion, or flow state and adjusts how it talks to the AI.
            </FeatureCard>

            <FeatureCard title="Universal AI support" icon="🌐">
              Works with ChatGPT, Claude, Gemini, Perplexity, You.com — any tool with a text box.
            </FeatureCard>

            <FeatureCard title="0.3ms WebSocket latency" icon="⚡">
              Real-time context updates from a local daemon.
            </FeatureCard>

            <FeatureCard title="Local-first and private" icon="🔒">
              Everything runs on localhost. No external servers. No data exhaust.
            </FeatureCard>

            <FeatureCard title="Strategic forgetting" icon="✨">
              Q-learning based compression (vismriti engine) that cuts an average of 36.6% tokens without losing meaning.
            </FeatureCard>
          </div>
        </Section>

        {/* Installation */}
        <Section className="bg-black">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-12 sm:mb-16 text-center">
            Get started in under 2 minutes
          </h2>

          <div className="space-y-8 sm:space-y-12 max-w-3xl mx-auto">
            <div>
              <h3 className="text-2xl sm:text-3xl font-bold mb-4 text-white">
                1. Install the daemon
              </h3>
              <CodeBlock>
{`pip install vidurai
vidurai start`}
              </CodeBlock>
              <p className="mt-4 text-slate-400">
                This runs the Vidurai daemon on http://localhost:7777.
              </p>
            </div>

            <div>
              <h3 className="text-2xl sm:text-3xl font-bold mb-4 text-white">
                2. Load the browser extension
              </h3>
              <ul className="space-y-2 text-slate-400 list-disc list-inside">
                <li>In Chrome: Load unpacked extension from the vidurai-extension folder.</li>
                <li>In Firefox: Load as a temporary add-on.</li>
              </ul>
            </div>

            <div>
              <h3 className="text-2xl sm:text-3xl font-bold mb-4 text-white">
                3. Press Ctrl+Shift+V (then Ctrl+V)
              </h3>
              <p className="text-slate-400 leading-relaxed">
                Vidurai prepares context.<br />
                You paste it into any AI chat box.<br />
                The AI suddenly knows what you've been doing.
              </p>
            </div>
          </div>
        </Section>

        {/* Philosophy */}
        <Section className="bg-gradient-to-b from-bg-soft to-bg-deep">
          <div className="text-center max-w-4xl mx-auto">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-8">
              <span className="text-vidurai-purple">विस्मृति भी विद्या है</span>
              <br />
              <span className="text-2xl sm:text-3xl lg:text-4xl mt-4 block text-slate-300">
                — Forgetting too is knowledge.
              </span>
            </h2>

            <div className="text-left space-y-6 text-base sm:text-lg lg:text-xl text-slate-400 leading-relaxed mt-12">
              <p>
                Vidurai is inspired by Indian philosophical ideas of memory and forgetting.
              </p>

              <p>
                Humans don't store every bit.<br />
                They compress experiences into meaning.
              </p>

              <p className="text-slate-300">
                Vidurai does the same for AI:
              </p>

              <ul className="space-y-2 list-disc list-inside pl-6">
                <li>It remembers what matters.</li>
                <li>It forgets what doesn't.</li>
                <li>It mediates instead of dumping.</li>
              </ul>

              <p className="pt-6 text-xl sm:text-2xl text-white text-center">
                Vidurai isn't just a tool.<br />
                <span className="text-vidurai-purple font-semibold">
                  It's a wise layer between you and your AI.
                </span>
              </p>
            </div>
          </div>
        </Section>

        {/* Final CTA */}
        <Section className="bg-black">
          <div className="text-center max-w-4xl mx-auto">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-6 sm:mb-8 text-balance">
              Make your AI feel like it has been{' '}
              <span className="text-vidurai-purple">sitting beside you.</span>
            </h2>

            <p className="text-lg sm:text-xl lg:text-2xl text-slate-400 mb-8 sm:mb-12">
              No more over-explaining.<br />
              No more missing context.<br />
              Just press Ctrl+Shift+V, and let Vidurai whisper.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6 mb-6">
              <Button href="https://github.com/chandantochandan/vidurai/releases" external variant="primary">
                Download Vidurai
              </Button>
              <Button href="https://github.com/chandantochandan/vidurai" external variant="secondary">
                View on GitHub
              </Button>
            </div>

            <div className="text-sm sm:text-base">
              <a
                href="https://docs.vidurai.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-vidurai-purple transition-colors underline"
              >
                Read the docs
              </a>
            </div>
          </div>
        </Section>
      </main>

      <Footer />
    </>
  )
}
