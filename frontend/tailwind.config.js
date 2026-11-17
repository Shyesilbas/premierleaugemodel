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
        // Semantic tokens mapped to CSS custom properties for light, dark, and forced-colors modes
        primary: {
          DEFAULT: 'rgb(var(--primary) / <alpha-value>)',
          hover: 'rgb(var(--primary-hover) / <alpha-value>)',
        },
        background: {
          primary: 'rgb(var(--bg-primary) / <alpha-value>)',
          secondary: 'rgb(var(--bg-secondary) / <alpha-value>)',
          tertiary: 'rgb(var(--bg-tertiary) / <alpha-value>)',
        },
        text: {
          primary: 'rgb(var(--text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--text-secondary) / <alpha-value>)',
          tertiary: 'rgb(var(--text-tertiary) / <alpha-value>)',
          muted: 'rgb(var(--text-muted) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--border-default) / <alpha-value>)',
          light: 'rgb(var(--border-light) / <alpha-value>)',
          focus: 'rgb(var(--border-focus) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--accent) / <alpha-value>)',
          hover: 'rgb(var(--accent-hover) / <alpha-value>)',
          soft: 'rgb(var(--accent-soft) / <alpha-value>)',
        },
        'card-border-hover': 'rgb(var(--card-border-hover) / <alpha-value>)',
        pitch: 'rgb(var(--pitch) / <alpha-value>)',
        status: {
          success: 'rgb(var(--status-success) / <alpha-value>)',
          error: 'rgb(var(--status-error) / <alpha-value>)',
          warning: 'rgb(var(--status-warning) / <alpha-value>)',
          info: 'rgb(var(--status-info) / <alpha-value>)',
          draw: 'rgb(var(--status-draw) / <alpha-value>)',
        },
      },
      aspectRatio: {
        pitch: '3 / 4',
        'pitch-wide': '4 / 3',
      },
      gridTemplateColumns: {
        versus: '1fr auto 1fr',
        'compare-row': 'minmax(0, 1fr) 8.5rem minmax(0, 1fr)',
        'manager-table': 'minmax(9rem, 1.5fr) repeat(6, minmax(3.25rem, 1fr))',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
