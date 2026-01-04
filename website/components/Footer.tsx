import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-bg-deep">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="text-center mb-8">
          <p className="text-lg sm:text-xl text-slate-300 mb-6">
            Vidurai — the mediator between human memory and AI understanding.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-sm sm:text-base">
            <Link href="/" className="text-slate-400 hover:text-vidurai-purple transition-colors">
              Home
            </Link>
            <Link href="/pricing" className="text-slate-400 hover:text-vidurai-purple transition-colors">
              Pricing
            </Link>
            <Link href="/changelog" className="text-slate-400 hover:text-vidurai-purple transition-colors">
              Changelog
            </Link>
            <a
              href="https://docs.vidurai.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-vidurai-purple transition-colors"
            >
              Docs
            </a>
            <a
              href="https://github.com/chandantochandan/vidurai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-vidurai-purple transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>

        <div className="text-center text-sm text-slate-500">
          <p>Made with विस्मृति • Local-first • Open source</p>
        </div>
      </div>
    </footer>
  )
}
