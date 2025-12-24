import { getItem } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// Formats supported by foliate-js reader
const READABLE_FORMATS = ['epub', 'mobi', 'azw', 'azw3', 'fb2', 'fbz', 'cbz'];

export const load: PageServerLoad = async ({ fetch, params }) => {
	const id = Number(params.id);
	if (isNaN(id)) {
		throw error(400, 'Invalid book ID');
	}

	try {
		const item = await getItem(id, fetch);

		// Find a readable file (prefer epub, then others)
		let readableFile = item.files.find((f) => f.format === 'epub');
		if (!readableFile) {
			readableFile = item.files.find((f) => READABLE_FORMATS.includes(f.format));
		}

		if (!readableFile) {
			throw error(404, 'No readable file available for this book');
		}

		return {
			item,
			readableFileId: readableFile.id,
			readableFormat: readableFile.format
		};
	} catch (e) {
		if ((e as { status?: number }).status) {
			throw e;
		}
		throw error(404, 'Book not found');
	}
};
