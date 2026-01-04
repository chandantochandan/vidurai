import { ReactNode } from 'react'

interface CodeBlockProps {
  children: ReactNode
}

export default function CodeBlock({ children }: CodeBlockProps) {
  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 sm:p-6 overflow-x-auto">
      <pre className="text-sm sm:text-base text-slate-300 font-mono whitespace-pre-wrap break-words">
        {children}
      </pre>
    </div>
  )
}
