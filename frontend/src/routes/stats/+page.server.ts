import { getStats, getReadingStats } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const [libraryStats, readingStats] = await Promise.all([
		getStats(fetch),
		getReadingStats(fetch)
	]);

	return {
		libraryStats,
		readingStats
	};
};
