/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    ...require('fi-glass/tailwind').content,
  ],
  theme: { extend: {} },
  plugins: [],
};
