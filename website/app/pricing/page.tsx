import type { Metadata } from 'next'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import Section from '@/components/Section'
import Button from '@/components/Button'

export const metadata: Metadata = {
  title: 'Pricing — Vidurai',
  description: 'Vidurai pricing plans. Start free with full features for individual developers.',
}

export default function Pricing() {
  return (
    <>
      <Header />

      <main>
        <Section className="bg-gradient-to-b from-bg-deep to-black pt-24">
          <div className="text-center max-w-4xl mx-auto mb-16">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
              Pricing
            </h1>
            <p className="text-lg sm:text-xl text-slate-400">
              Vidurai is built for developers first.<br />
              We start simple and honest.
            </p>
          </div>

          {/* Pricing Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 max-w-6xl mx-auto mb-16">
            {/* Community Plan */}
            <div className="bg-bg-soft border-2 border-vidurai-purple rounded-xl p-8 hover:shadow-lg hover:shadow-vidurai-purple/20 transition-all">
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">Community</h3>
                <p className="text-slate-400">For individual developers</p>
              </div>

              <div className="mb-8">
                <div className="text-5xl font-bold text-vidurai-purple mb-2">Free</div>
                <p className="text-slate-400">Forever</p>
              </div>

              <ul className="space-y-4 mb-8 text-slate-300">
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Local daemon</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Browser extension</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Intelligent context mediator</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Strategic forgetting</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>All core features</span>
                </li>
              </ul>

              <Button href="https://github.com/chandantochandan/vidurai/releases" external variant="primary" className="w-full text-center">
                Download Now
              </Button>
            </div>

            {/* Pro Plan */}
            <div className="bg-bg-soft border border-slate-700 rounded-xl p-8 opacity-75">
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">Pro</h3>
                <p className="text-slate-400">For power users</p>
              </div>

              <div className="mb-8">
                <div className="text-5xl font-bold text-slate-500 mb-2">Coming soon</div>
              </div>

              <ul className="space-y-4 mb-8 text-slate-400">
                <li className="flex items-start">
                  <span className="text-slate-600 mr-3 mt-1">✓</span>
                  <span>Multi-project intelligence</span>
                </li>
                <li className="flex items-start">
                  <span className="text-slate-600 mr-3 mt-1">✓</span>
                  <span>Rich timelines of what changed</span>
                </li>
                <li className="flex items-start">
                  <span className="text-slate-600 mr-3 mt-1">✓</span>
                  <span>Team context presets</span>
                </li>
                <li className="flex items-start">
                  <span className="text-slate-600 mr-3 mt-1">✓</span>
                  <span>Priority updates</span>
                </li>
              </ul>

              <button
                disabled
                className="w-full px-6 py-3 bg-slate-700 text-slate-400 rounded-lg font-semibold cursor-not-allowed"
              >
                Coming Soon
              </button>
            </div>

            {/* Enterprise Plan */}
            <div className="bg-bg-soft border border-slate-700 rounded-xl p-8">
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">Enterprise</h3>
                <p className="text-slate-400">For teams and companies</p>
              </div>

              <div className="mb-8">
                <div className="text-5xl font-bold text-white mb-2">Custom</div>
              </div>

              <ul className="space-y-4 mb-8 text-slate-300">
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>On-prem deployment</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Custom integrations</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Security reviews</span>
                </li>
                <li className="flex items-start">
                  <span className="text-vidurai-purple mr-3 mt-1">✓</span>
                  <span>Dedicated support</span>
                </li>
              </ul>

              <a
                href="mailto:contact@vidurai.ai"
                className="block w-full px-6 py-3 bg-transparent border-2 border-vidurai-purple text-vidurai-purple rounded-lg font-semibold text-center hover:bg-vidurai-purple hover:text-white transition-all"
              >
                Contact Us
              </a>
            </div>
          </div>

          {/* FAQ */}
          <div className="max-w-3xl mx-auto mt-24">
            <h2 className="text-3xl sm:text-4xl font-bold mb-12 text-center">
              Frequently Asked Questions
            </h2>

            <div className="space-y-8">
              <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-4">
                  Is Vidurai open source?
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  Yes! Vidurai is fully open source and available on GitHub. You can inspect the code,
                  contribute features, or fork it for your own use. We believe transparency is essential
                  for developer tools.
                </p>
              </div>

              <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-4">
                  Does my data leave my machine?
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  No, never. Vidurai runs entirely on localhost (http://localhost:7777). All file watching,
                  terminal monitoring, and context processing happens locally. There are no external servers,
                  no telemetry, and no data uploads. Your code and context remain 100% private.
                </p>
              </div>

              <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-4">
                  Can I use Vidurai at work?
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  Absolutely. Since Vidurai is local-first and doesn't send data anywhere, it's safe to use
                  in corporate environments. Many developers use it to improve their productivity with AI tools
                  while keeping proprietary code secure. For enterprise deployments with additional compliance
                  requirements, contact us about our Enterprise plan.
                </p>
              </div>

              <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-4">
                  Which AI tools does Vidurai work with?
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  Vidurai works with any AI tool that has a text input box. This includes ChatGPT, Claude,
                  Gemini, Perplexity, You.com, and many others. The browser extension uses clipboard-based
                  injection for universal compatibility.
                </p>
              </div>
            </div>
          </div>
        </Section>
      </main>

      <Footer />
    </>
  )
}
