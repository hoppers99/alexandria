import { getPile } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const pileId = parseInt(params.id, 10);

	if (isNaN(pileId)) {
		throw error(400, 'Invalid pile ID');
	}

	try {
		const pile = await getPile(pileId, fetch);
		return { pile };
	} catch (err) {
		throw error(404, 'Pile not found');
	}
};
