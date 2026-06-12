/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    // fi-glass ships Tailwind utility classes in its dist — must be scanned explicitly.
    // See og118 VALIDATION_REPORT finding #3.
    '../../packages/fi-glass/dist/**/*.{js,mjs}',
  ],
  theme: { extend: {} },
  plugins: [],
};
