import { getAuthors } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const page = Number(url.searchParams.get('page')) || 1;
	const sort = url.searchParams.get('sort') || 'name';
	const order = url.searchParams.get('order') || 'asc';
	const q = url.searchParams.get('q') || undefined;

	const data = await getAuthors({ page, per_page: 50, sort, order, q }, fetch);

	return {
		...data,
		sort,
		order,
		q
	};
};
