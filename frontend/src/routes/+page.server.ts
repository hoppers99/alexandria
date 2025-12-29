import { getRecentItems, getStats, getCurrentlyReading } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const [recentItems, stats, currentlyReading] = await Promise.all([
		getRecentItems(12, fetch, true), // include piles
		getStats(fetch),
		getCurrentlyReading(6, fetch, true).catch(() => ({ items: [] })) // include piles
	]);

	return {
		recentItems,
		stats,
		currentlyReading: currentlyReading.items
	};
};
