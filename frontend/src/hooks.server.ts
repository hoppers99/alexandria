import type { Handle } from '@sveltejs/kit';
import { dev } from '$app/environment';

// In production, proxy /api requests to the backend service
// In dev mode, Vite handles the proxy
const API_HOST = process.env.API_HOST || 'localhost';
const API_PORT = process.env.API_PORT || '8000';
const API_BASE_URL = `http://${API_HOST}:${API_PORT}`;

export const handle: Handle = async ({ event, resolve }) => {
	// In dev mode, let Vite's proxy handle /api requests
	// In production, proxy them to the backend service
	if (!dev && event.url.pathname.startsWith('/api/')) {
		const apiUrl = `${API_BASE_URL}${event.url.pathname}${event.url.search}`;

		const response = await fetch(apiUrl, {
			method: event.request.method,
			headers: event.request.headers,
			body: event.request.method !== 'GET' && event.request.method !== 'HEAD'
				? await event.request.arrayBuffer()
				: undefined,
			// @ts-expect-error duplex is required for streaming but not in types
			duplex: 'half'
		});

		return new Response(response.body, {
			status: response.status,
			statusText: response.statusText,
			headers: response.headers
		});
	}

	return resolve(event);
};
