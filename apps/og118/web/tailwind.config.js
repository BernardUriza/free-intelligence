/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    // fi-glass primitives ship Tailwind utility classes baked into their dist.
    // Tailwind ignores node_modules, so we must scan the workspace dist directly
    // for the classes used by MessageBubble/MessageList/MessageContent to be
    // generated. (VALIDATION_REPORT finding #3: implicit Tailwind dependency.)
    '../../packages/fi-glass/dist/**/*.{js,mjs}',
  ],
  theme: { extend: {} },
  plugins: [],
};
