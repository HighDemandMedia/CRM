import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  // Calendar primitives and app values must share the same date constructors.
  resolve: { dedupe: ['@internationalized/date'] },
  server: { port: 5181, strictPort: true }
});
