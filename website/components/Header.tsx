import Link from 'next/link'
import Image from 'next/image'

export default function Header() {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-lg bg-black/80 border-b border-slate-800">
      <nav className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity group">
            <Image
              src="/kosha-icon.png"
              alt="Vidurai 3 Kosha Logo"
              width={40}
              height={40}
              className="rounded-lg"
            />
            <span className="text-xl font-bold text-vidurai-purple">
              Vidurai
            </span>
          </Link>

          <div className="flex items-center gap-6 sm:gap-8">
            <Link href="/pricing" className="text-sm sm:text-base text-slate-300 hover:text-white transition-colors">
              Pricing
            </Link>
            <Link href="/changelog" className="text-sm sm:text-base text-slate-300 hover:text-white transition-colors">
              Changelog
            </Link>
            <a
              href="https://docs.vidurai.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm sm:text-base text-slate-300 hover:text-white transition-colors"
            >
              Docs
            </a>
            <a
              href="https://github.com/chandantochandan/vidurai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm sm:text-base text-slate-300 hover:text-white transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </nav>
    </header>
  )
}
