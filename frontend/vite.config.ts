import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// When running in Docker, use host.docker.internal to reach the host
const apiHost = process.env.API_HOST || 'localhost';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: `http://${apiHost}:8000`,
				changeOrigin: true,
			},
			'/graphql': {
				target: `http://${apiHost}:8000`,
				changeOrigin: true,
			},
		}
	},
	optimizeDeps: {
		// foliate-js needs special handling as it uses dynamic imports internally
		exclude: ['foliate-js']
	}
});
