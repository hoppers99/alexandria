import { getItem } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const id = Number(params.id);
	if (isNaN(id)) {
		throw error(400, 'Invalid book ID');
	}

	try {
		const item = await getItem(id, fetch);
		return { item };
	} catch (e) {
		throw error(404, 'Book not found');
	}
};
