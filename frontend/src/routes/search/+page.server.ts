import { getItems, getAuthors, getSeries } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const q = url.searchParams.get('q') || '';
	const page = Number(url.searchParams.get('page')) || 1;

	if (!q.trim()) {
		return {
			q: '',
			items: null,
			authors: null,
			series: null
		};
	}

	// Search across books, authors, and series in parallel
	const [items, authors, series] = await Promise.all([
		getItems({ q, page, per_page: 24 }, fetch),
		getAuthors({ q, per_page: 10 }, fetch),
		getSeries({ q, per_page: 10 }, fetch)
	]);

	return {
		q,
		page,
		items,
		authors,
		series
	};
};
