import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: '../backend/oryups/static',
      assets: '../backend/oryups/static',
      fallback: 'index.html',
      precompress: false,
      strict: false
    }),
    appDir: 'assets/_app'
  }
};

export default config;
