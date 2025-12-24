import { getSeries } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const page = Number(url.searchParams.get('page')) || 1;
	const sort = url.searchParams.get('sort') || 'name';
	const order = url.searchParams.get('order') || 'asc';
	const q = url.searchParams.get('q') || undefined;

	const data = await getSeries({ page, per_page: 24, sort, order, q }, fetch);

	return {
		...data,
		sort,
		order,
		q
	};
};
