import { getReviewQueue, getReviewStats } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const skip = parseInt(url.searchParams.get('skip') || '0', 10);
	const format = url.searchParams.get('format') || undefined;

	const [queue, stats] = await Promise.all([
		getReviewQueue({ skip, limit: 1, format }, fetch),
		getReviewStats(fetch)
	]);

	return {
		queue,
		stats,
		currentSkip: skip,
		currentFormat: format
	};
};
