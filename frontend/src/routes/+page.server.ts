import { getRecentItems, getStats } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const [recentItems, stats] = await Promise.all([
		getRecentItems(12, fetch),
		getStats(fetch)
	]);

	return {
		recentItems,
		stats
	};
};
