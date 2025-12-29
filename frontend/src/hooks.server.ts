import type { Handle } from '@sveltejs/kit';
import { dev } from '$app/environment';
import { redirect } from '@sveltejs/kit';

// In production, proxy /api requests to the backend service
// In dev mode, Vite handles the proxy
const API_HOST = process.env.API_HOST || 'localhost';
const API_PORT = process.env.API_PORT || '8000';
const API_BASE_URL = `http://${API_HOST}:${API_PORT}`;

// Public paths that don't require authentication
const PUBLIC_PATHS = ['/login'];

export const handle: Handle = async ({ event, resolve }) => {
	// Initialize user as null
	event.locals.user = null;

	// Don't check auth for API routes or public paths
	const isApiRoute = event.url.pathname.startsWith('/api/');
	const isPublicPath = PUBLIC_PATHS.includes(event.url.pathname);

	// Try to get current user from session cookie (only for non-API, non-public routes)
	if (!isApiRoute && !isPublicPath) {
		try {
			// Get the session cookie from the incoming request
			const sessionCookie = event.cookies.get('alexandria_session');

			if (sessionCookie) {
				// Forward the cookie to the backend
				const response = await event.fetch(`${dev ? '' : API_BASE_URL}/api/auth/me`, {
					headers: {
						Cookie: `alexandria_session=${sessionCookie}`
					}
				});
				if (response.ok) {
					event.locals.user = await response.json();
				}
			}
		} catch (error) {
			// Session invalid or expired, user stays null
		}

		// Redirect to login if not authenticated
		if (!event.locals.user) {
			const redirectTo = event.url.pathname + event.url.search;
			throw redirect(302, `/login?redirect=${encodeURIComponent(redirectTo)}`);
		}
	}

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
