import { getItems } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const page = Number(url.searchParams.get('page')) || 1;
	const sort = url.searchParams.get('sort') || 'date_added';
	const order = url.searchParams.get('order') || 'desc';
	const q = url.searchParams.get('q') || undefined;
	const format = url.searchParams.get('format') || undefined;
	const media_type = url.searchParams.get('media_type') || undefined;

	const data = await getItems({ page, per_page: 24, sort, order, q, format, media_type }, fetch);

	return {
		...data,
		sort,
		order,
		q,
		format,
		media_type
	};
};
