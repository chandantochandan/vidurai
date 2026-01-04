import { ReactNode } from 'react'

interface FeatureCardProps {
  title: string
  children: ReactNode
  icon?: string
}

export default function FeatureCard({ title, children, icon }: FeatureCardProps) {
  return (
    <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8 hover:border-vidurai-purple/50 transition-all duration-300 hover:shadow-lg hover:shadow-vidurai-purple/10 hover:-translate-y-1">
      {icon && (
        <div className="text-3xl sm:text-4xl mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-xl sm:text-2xl font-semibold mb-3 sm:mb-4 text-white">
        {title}
      </h3>
      <div className="text-slate-400 leading-relaxed">
        {children}
      </div>
    </div>
  )
}
