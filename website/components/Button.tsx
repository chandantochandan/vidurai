import Link from 'next/link'
import { ReactNode } from 'react'

interface ButtonProps {
  href: string
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost'
  external?: boolean
  className?: string
}

export default function Button({
  href,
  children,
  variant = 'primary',
  external = false,
  className = ''
}: ButtonProps) {
  const baseStyles = "inline-block px-6 py-3 sm:px-8 sm:py-4 rounded-lg font-semibold text-base sm:text-lg transition-all duration-200"

  const variants = {
    primary: "bg-vidurai-purple hover:bg-purple-600 text-white shadow-lg shadow-vidurai-purple/20 hover:shadow-vidurai-purple/40 hover:scale-105",
    secondary: "bg-transparent border-2 border-vidurai-purple text-vidurai-purple hover:bg-vidurai-purple hover:text-white",
    ghost: "bg-transparent text-slate-300 hover:text-white hover:bg-slate-800"
  }

  const combinedClassName = `${baseStyles} ${variants[variant]} ${className}`

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={combinedClassName}
      >
        {children}
      </a>
    )
  }

  return (
    <Link href={href} className={combinedClassName}>
      {children}
    </Link>
  )
}
