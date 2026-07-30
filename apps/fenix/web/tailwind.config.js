/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    // HALLAZGO-2 (ver .claude/EXPERIMENTO.md): fi-glass hornea utilidades Tailwind
    // en su dist y Tailwind no escanea node_modules, así que TODO consumer debe
    // repetir esta línea o la UI del framework sale sin estilos.
    '../../packages/fi-glass/dist/**/*.{js,mjs}',
  ],
  theme: { extend: {} },
  plugins: [],
};
