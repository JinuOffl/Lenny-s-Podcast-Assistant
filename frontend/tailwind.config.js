/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      /* ── Our custom design tokens ──────────────────────────────────────── */
      colors: {
        bg: {
          base:     '#09090b',
          surface:  '#18181b',
          elevated: '#27272a',
        },
        accent: {
          primary:   '#f97316',
          secondary: '#fb923c',
          muted:     '#431407',
        },
        text: {
          primary:   '#fafafa',
          secondary: '#a1a1aa',
          muted:     '#71717a',
        },
        skill: {
          qa:       '#22d3ee',
          ship30:   '#a78bfa',
          artifact: '#4ade80',
        },

        /* ── shadcn CSS variable colors (used by assistant-ui Thread) ─────── */
        background:  'hsl(var(--background))',
        foreground:  'hsl(var(--foreground))',
        card: {
          DEFAULT:    'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT:    'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT:    'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT:    'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT:    'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT:    'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
          primary:   '#f97316',
          secondary: '#fb923c',
          muted:     '#431407',
        },
        destructive: {
          DEFAULT:    'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border:  'hsl(var(--border))',
        input:   'hsl(var(--input))',
        ring:    'hsl(var(--ring))',
        chart: {
          1: 'hsl(var(--chart-1))',
          2: 'hsl(var(--chart-2))',
          3: 'hsl(var(--chart-3))',
          4: 'hsl(var(--chart-4))',
          5: 'hsl(var(--chart-5))',
        },
      },

      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        xl: 'calc(var(--radius) + 4px)',
        '2xl': 'calc(var(--radius) + 8px)',
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },

      animation: {
        'pulse-dot':    'pulse 1.2s ease-in-out infinite',
        'fade-in':      'fadeIn 0.2s ease-out',
        'fade-up':      'fadeUp 0.3s ease-out',
        'glow-pulse':   'glowPulse 2s ease-in-out infinite',
        /* assistant-ui animations */
        'in':                     'fadeIn 0.2s ease-out',
        'fade-in-0':              'fadeIn 0.15s ease-out',
        'zoom-in-50':             'zoomIn50 0.15s ease-out',
        'zoom-in-75':             'zoomIn75 0.15s ease-out',
        'zoom-in-95':             'zoomIn95 0.15s ease-out',
        'zoom-out-95':            'zoomOut95 0.1s ease-in',
        'fade-out-0':             'fadeOut 0.1s ease-in',
        'slide-in-from-top-2':    'slideInFromTop 0.2s ease-out',
        'slide-in-from-bottom-1': 'slideInFromBottom1 0.15s ease-out',
        'slide-in-from-bottom-2': 'slideInFromBottom2 0.2s ease-out',
        'slide-in-from-left-2':   'slideInFromLeft 0.2s ease-out',
        'slide-in-from-right-2':  'slideInFromRight 0.2s ease-out',
        'collapsible-down':       'collapsibleDown 0.2s ease-out',
        'collapsible-up':         'collapsibleUp 0.2s ease-out',
      },
      keyframes: {
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)'   },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%':   { opacity: '1' },
          '100%': { opacity: '0' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 12px rgba(249,115,22,0.2)' },
          '50%':      { boxShadow: '0 0 24px rgba(249,115,22,0.45)' },
        },
        zoomIn50: {
          '0%':   { transform: 'scale(0.5)', opacity: '0' },
          '100%': { transform: 'scale(1)',   opacity: '1' },
        },
        zoomIn75: {
          '0%':   { transform: 'scale(0.75)', opacity: '0' },
          '100%': { transform: 'scale(1)',    opacity: '1' },
        },
        zoomIn95: {
          '0%':   { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)',    opacity: '1' },
        },
        zoomOut95: {
          '0%':   { transform: 'scale(1)',    opacity: '1' },
          '100%': { transform: 'scale(0.95)', opacity: '0' },
        },
        slideInFromTop: {
          '0%':   { transform: 'translateY(-4px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        slideInFromBottom1: {
          '0%':   { transform: 'translateY(4px)',  opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        slideInFromBottom2: {
          '0%':   { transform: 'translateY(8px)',  opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        slideInFromLeft: {
          '0%':   { transform: 'translateX(-8px)', opacity: '0' },
          '100%': { transform: 'translateX(0)',    opacity: '1' },
        },
        slideInFromRight: {
          '0%':   { transform: 'translateX(8px)',  opacity: '0' },
          '100%': { transform: 'translateX(0)',    opacity: '1' },
        },
        collapsibleDown: {
          '0%':   { height: '0' },
          '100%': { height: 'var(--radix-collapsible-content-height, auto)' },
        },
        collapsibleUp: {
          '0%':   { height: 'var(--radix-collapsible-content-height, auto)' },
          '100%': { height: '0' },
        },
      },
    },
  },
  plugins: [],
}
