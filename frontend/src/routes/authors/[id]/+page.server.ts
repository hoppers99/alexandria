import { getAuthor, getItems } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const id = Number(params.id);
	if (isNaN(id)) {
		throw error(400, 'Invalid author ID');
	}

	const page = Number(url.searchParams.get('page')) || 1;

	try {
		const [author, books] = await Promise.all([
			getAuthor(id, fetch),
			getItems({ author_id: id, page, per_page: 24 }, fetch)
		]);

		return {
			author,
			books,
			page
		};
	} catch (e) {
		throw error(404, 'Author not found');
	}
};
