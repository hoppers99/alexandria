import { getSeriesDetail } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	try {
		const series = await getSeriesDetail(params.name, fetch, true); // include piles
		return { series };
	} catch (e) {
		throw error(404, 'Series not found');
	}
};
