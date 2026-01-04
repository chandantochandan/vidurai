import type { Metadata } from 'next'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import Section from '@/components/Section'
import ChangelogItem from '@/components/ChangelogItem'

export const metadata: Metadata = {
  title: 'Changelog — Vidurai',
  description: 'See what\'s new in Vidurai. Track features, improvements, and updates.',
}

export default function Changelog() {
  return (
    <>
      <Header />

      <main>
        <Section className="bg-gradient-to-b from-bg-deep to-black pt-24">
          <div className="text-center max-w-4xl mx-auto mb-16">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
              Changelog
            </h1>
            <p className="text-lg sm:text-xl text-slate-400">
              Vidurai moves fast.<br />
              Here's what has changed — and why it matters.
            </p>
          </div>

          {/* Changelog Entries */}
          <div className="max-w-4xl mx-auto">
            <ChangelogItem version="v2.5.0" title="Human–AI Whisperer">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Human-AI Whisperer layer for natural-language context
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Emotional state detection now recognizes panic, confusion, and flow states
                </li>
                <li>
                  <strong className="text-white">Enhanced:</strong> Smarter context trimming with vismriti engine
                </li>
                <li>
                  <strong className="text-white">Fixed:</strong> Better stability for WebSocket connections
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v2.4.0" title="Universal Injection">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Robust multi-method context injection for ChatGPT, Claude, Gemini, Perplexity, and others
                </li>
                <li>
                  <strong className="text-white">New:</strong> Clipboard-based fallback for maximum compatibility
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Better platform detection in the browser extension
                </li>
                <li>
                  <strong className="text-white">Fixed:</strong> React injection edge cases resolved
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v2.3.0" title="Terminal Intelligence">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Correlates terminal commands with resulting errors
                </li>
                <li>
                  <strong className="text-white">New:</strong> Maps exit codes to natural explanations
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Reduces noisy log lines so only the important parts reach the AI
                </li>
                <li>
                  <strong className="text-white">Enhanced:</strong> Better understanding of build tool outputs (npm, cargo, go, etc.)
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v2.2.0" title="File Intelligence">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Smart file watcher that identifies which changes matter
                </li>
                <li>
                  <strong className="text-white">New:</strong> Ignores node_modules, .git, and other noise directories by default
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Faster file change detection with debouncing
                </li>
                <li>
                  <strong className="text-white">Fixed:</strong> Memory leaks in long-running daemon sessions
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v2.1.0" title="WebSocket Real-Time">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Real-time WebSocket connection (0.3ms latency)
                </li>
                <li>
                  <strong className="text-white">New:</strong> Browser extension now receives instant updates
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Daemon startup time reduced by 40%
                </li>
                <li>
                  <strong className="text-white">Fixed:</strong> Port conflicts when multiple instances attempt to start
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v2.0.0" title="Strategic Forgetting (विस्मृति)">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Q-learning based compression engine (vismriti)
                </li>
                <li>
                  <strong className="text-white">New:</strong> 36.6% average token reduction without losing meaning
                </li>
                <li>
                  <strong className="text-white">Breaking:</strong> New context format (not compatible with v1.x)
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Semantic understanding of what matters vs. noise
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v1.5.0" title="Browser Extension">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Universal browser extension for Chrome and Firefox
                </li>
                <li>
                  <strong className="text-white">New:</strong> Ctrl+Shift+V keyboard shortcut to prepare context
                </li>
                <li>
                  <strong className="text-white">Improved:</strong> Clipboard integration for seamless pasting
                </li>
              </ul>
            </ChangelogItem>

            <ChangelogItem version="v1.0.0" title="Initial Release">
              <ul className="space-y-3 list-disc list-inside">
                <li>
                  <strong className="text-white">New:</strong> Local daemon running on localhost:7777
                </li>
                <li>
                  <strong className="text-white">New:</strong> Basic file and terminal watching
                </li>
                <li>
                  <strong className="text-white">New:</strong> Context export for AI tools
                </li>
              </ul>
            </ChangelogItem>

            {/* Footer note */}
            <div className="mt-16 p-6 sm:p-8 bg-bg-soft border border-slate-800 rounded-xl text-center">
              <p className="text-slate-400 italic">
                Vidurai is evolving constantly. विस्मृति भी विद्या है — sometimes we forget features that don't deserve to stay.
              </p>
            </div>
          </div>
        </Section>
      </main>

      <Footer />
    </>
  )
}
