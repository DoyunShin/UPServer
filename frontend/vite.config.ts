import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/get': 'http://localhost:5000',
      '/favicon.ico': 'http://localhost:5000',
      '/robots.txt': 'http://localhost:5000',
      '^/[^/?#]+$': {
        target: 'http://localhost:5000',
        bypass: (req) => (req.method === 'GET' ? req.url : undefined)
      },
      '^/[^/?#]+/[^/?#]+$': {
        target: 'http://localhost:5000',
        bypass: (req) => (req.method === 'GET' ? req.url : undefined)
      }
    }
  }
});
