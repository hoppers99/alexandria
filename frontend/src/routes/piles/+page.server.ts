import { getPiles } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const pilesData = await getPiles(fetch);

	return {
		piles: pilesData.piles
	};
};
