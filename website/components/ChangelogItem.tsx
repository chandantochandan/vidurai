import { ReactNode } from 'react'

interface ChangelogItemProps {
  version: string
  title: string
  children: ReactNode
}

export default function ChangelogItem({ version, title, children }: ChangelogItemProps) {
  return (
    <div className="bg-bg-soft border border-slate-800 rounded-xl p-6 sm:p-8 mb-6 sm:mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <h3 className="text-2xl sm:text-3xl font-bold text-white">
          {version}
        </h3>
        <span className="text-lg sm:text-xl text-vidurai-purple font-semibold">
          {title}
        </span>
      </div>
      <div className="text-slate-400 space-y-2">
        {children}
      </div>
    </div>
  )
}
