/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Semantic tokens (see DESIGN.md)
        primary: { DEFAULT: '#0f172a', hover: '#1e293b' },
        background: { primary: '#ffffff', secondary: '#f8fafc', tertiary: '#f1f5f9' },
        text: { primary: '#0f172a', secondary: '#475569', tertiary: '#64748b', muted: '#94a3b8' },
        border: { DEFAULT: '#e2e8f0', light: '#f1f5f9', focus: '#0f172a' },
        'card-border-hover': '#cbd5e1',
        status: { success: '#047857', error: '#b91c1c', warning: '#b45309', info: '#1d4ed8' },
        pl: {
          dark: '#05070c',
          card: '#0c101a',
          cardHover: '#131926',
          border: 'rgba(255, 255, 255, 0.08)',
          purple: '#38003c',
          green: '#00ff87',
          cyan: '#04f5ff',
          pink: '#e90052',
          yellow: '#ffdc00',
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-green': '0 0 25px rgba(0, 255, 135, 0.25)',
        'glow-cyan': '0 0 25px rgba(4, 245, 255, 0.25)',
        'glow-purple': '0 0 30px rgba(56, 0, 60, 0.6)',
        'premium': '0 10px 40px -10px rgba(0,0,0,0.7)',
      }
    },
  },
  plugins: [],
}
