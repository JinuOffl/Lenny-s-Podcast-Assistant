/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      /* ── Nothing × ChatGPT monochromatic palette ─────────────────────────── */
      colors: {
        /* Backgrounds */
        bg: {
          base:     '#0D0D0D',   /* app canvas — near-pure black (Nothing) */
          surface:  '#141414',   /* sidebar, cards */
          elevated: '#1C1C1C',   /* hover, inputs */
          'user-msg': '#1F1F1F', /* user message bubble */
        },
        /* Borders */
        border: {
          DEFAULT: '#262626',
          subtle:  '#1E1E1E',
        },
        /* Text */
        text: {
          primary:   '#F2F2F2',
          secondary: '#888888',
          muted:     '#555555',
        },
        /* Accent — white only, like Nothing */
        accent: '#FFFFFF',
        /* Skill colours — muted, not neon */
        skill: {
          qa:       '#5B8DEF',   /* soft blue */
          ship30:   '#8B6EE8',   /* soft purple */
          artifact: '#4CAF82',   /* soft green */
        },
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },

      borderRadius: {
        '4xl': '2rem',
      },

      animation: {
        'fade-in':  'fade-in 0.18s ease-out both',
        'fade-up':  'fade-up 0.22s ease-out both',
        'slide-in': 'slide-in 0.2s ease-out both',
      },

      keyframes: {
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in': {
          '0%':   { opacity: '0', transform: 'translateX(-8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
