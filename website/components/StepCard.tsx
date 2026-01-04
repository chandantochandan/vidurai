import { ReactNode } from 'react'

interface StepCardProps {
  number: string
  title: string
  children: ReactNode
}

export default function StepCard({ number, title, children }: StepCardProps) {
  return (
    <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8 hover:border-vidurai-purple/50 transition-all duration-300">
      <div className="flex items-start gap-4 mb-4">
        <div className="flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 bg-vidurai-purple rounded-full flex items-center justify-center text-white font-bold text-lg sm:text-xl">
          {number}
        </div>
        <h3 className="text-lg sm:text-xl font-semibold text-white pt-2">
          {title}
        </h3>
      </div>
      <div className="text-slate-400 leading-relaxed pl-0 sm:pl-16">
        {children}
      </div>
    </div>
  )
}
