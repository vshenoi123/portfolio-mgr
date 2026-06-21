/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          green: '#22c55e',
          'green-dark': '#16a34a',
          'green-light': '#4ade80',
          bg: '#0a0a0a',
          'bg-light': '#111111',
          'bg-card': '#1a1a1a',
          'bg-hover': '#222222',
          border: '#2a2a2a',
          text: '#e5e5e5',
          'text-muted': '#888888',
          red: '#ef4444',
          yellow: '#eab308',
          blue: '#3b82f6',
        },
      },
      fontFamily: {
        mono: ['var(--font-plex-mono)', 'monospace'],
        sans: ['var(--font-plex-sans)', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scanline': 'scanline 8s linear infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
      },
    },
  },
  plugins: [],
};
