import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), 'VITE_');
	return {
		plugins: [sveltekit()],
		server: {
			proxy: {
				'/api': {
					target: env.VITE_PROXY_TARGET,
					changeOrigin: true,
				},
				                '/get': {
									target: 'https://up.ory.kr',
									changeOrigin: true,
								},                '/info': {
													target: env.VITE_PROXY_TARGET,
													changeOrigin: true,
												},
												                '/': {
																	target: env.VITE_PROXY_TARGET,
																	changeOrigin: true,
																	bypass: (req, res, options) => {
																		if (req.method !== 'PUT') {
																			return req.url;
																		}
																	}
																}			}
		}
	}
});
