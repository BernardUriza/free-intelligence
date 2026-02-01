/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./src-tauri/**/*.{html,js,ts}",
  ],
  theme: {
    extend: {
      colors: {
        // Mapear variables CSS existentes
        'app-bg': 'var(--bg)',
        'app-surface': 'var(--surface)',
        'app-surface-hover': 'var(--surface-hover)',
        'app-border': 'var(--border)',
        'app-border-bright': 'var(--border-bright)',
        'app-text': 'var(--text)',
        'app-text-dim': 'var(--text-dim)',
        'app-accent': 'var(--accent)',
        'app-accent-bright': 'var(--accent-bright)',
        'app-success': 'var(--success)',
        'app-error': 'var(--error)',
        'app-warning': 'var(--warning)',
      },
    },
  },
  plugins: [],
}
