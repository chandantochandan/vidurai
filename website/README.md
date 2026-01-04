# Vidurai Website

Production-grade marketing website for Vidurai — The Human–AI Context Layer.

## Tech Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **TailwindCSS**
- **Deployed on Vercel**

## Getting Started

### Install dependencies

```bash
npm install
```

### Run development server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the site.

### Build for production

```bash
npm run build
```

### Start production server

```bash
npm start
```

## Project Structure

```
vidurai-website-nextjs/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Homepage
│   ├── pricing/
│   │   └── page.tsx        # Pricing page
│   ├── changelog/
│   │   └── page.tsx        # Changelog page
│   └── globals.css         # Global styles
├── components/
│   ├── Header.tsx          # Site header/navigation
│   ├── Footer.tsx          # Site footer
│   ├── Hero.tsx            # Hero section
│   ├── Section.tsx         # Reusable section wrapper
│   ├── Button.tsx          # Button component
│   ├── FeatureCard.tsx     # Feature card
│   ├── StepCard.tsx        # Step card (numbered)
│   ├── CodeBlock.tsx       # Code display block
│   └── ChangelogItem.tsx   # Changelog entry
├── tailwind.config.ts      # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies
```

## Features

- ✅ Mobile-first responsive design
- ✅ SEO optimized with Next.js Metadata API
- ✅ Semantic HTML for accessibility
- ✅ Fast performance (targeting Lighthouse 95+)
- ✅ Clean, maintainable component architecture
- ✅ Vidurai brand colors and typography
- ✅ Smooth animations and transitions

## Brand Colors

- **Vidurai Purple**: `#8246FF`
- **Background Deep**: `#050816`
- **Background Soft**: `#0B1020`

## Philosophy

विस्मृति भी विद्या है — "Forgetting too is knowledge."

---

Made with विस्मृति • Local-first • Open source
