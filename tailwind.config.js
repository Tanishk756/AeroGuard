/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './apps/**/*.{ts,tsx}',
    './packages/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        background: '#07131d',
        panel: '#0d1b2a',
        panelAlt: '#13273c',
        accent: '#4ec9f5',
        accentStrong: '#7dd3fc',
        warning: '#f59e0b',
        danger: '#ef4444',
        success: '#22c55e',
        muted: '#8ca8bc'
      },
      boxShadow: {
        panel: '0 0 0 1px rgba(148, 163, 184, 0.15), 0 10px 30px rgba(2, 6, 23, 0.35)'
      }
    }
  },
  plugins: []
};
