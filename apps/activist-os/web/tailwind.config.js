/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    '../../packages/fi-glass/dist/**/*.{js,mjs}',
  ],
  theme: { extend: {} },
  plugins: [],
};
