import Button from './Button'

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-bg-deep via-bg-soft to-black">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-vidurai-purple/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse delay-700"></div>
      </div>

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 lg:py-32">
        <div className="text-center">
          {/* Main title */}
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold mb-6 sm:mb-8">
            <span className="block text-white mb-2 sm:mb-4">Vidurai</span>
            <span className="block text-vidurai-purple text-balance">
              The Human–AI Context Layer
            </span>
          </h1>

          {/* Sanskrit tagline */}
          <p className="text-lg sm:text-xl lg:text-2xl text-slate-300 mb-4 sm:mb-6 italic">
            विस्मृति भी विद्या है — "Forgetting too is knowledge."
          </p>

          {/* Description */}
          <div className="max-w-4xl mx-auto mb-8 sm:mb-12 space-y-3 sm:space-y-4 text-base sm:text-lg lg:text-xl text-slate-400 leading-relaxed">
            <p>
              A local, intelligent mediator between you and every AI.
            </p>
            <p>
              Vidurai watches your work, understands your intent, forgets the noise,
              and whispers exactly the right context to any AI — instantly.
            </p>
          </div>

          {/* CTA buttons */}
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
      </div>
    </section>
  )
}
