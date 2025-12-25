// API client for Alexandria

// Base URL - in SSR context, need absolute URL to backend
const API_BASE = '/api';

export interface ItemSummary {
	id: number;
	uuid: string;
	title: string;
	subtitle: string | null;
	authors: string[];
	cover_url: string | null;
	series_name: string | null;
	series_index: number | null;
	media_type: string;
	formats: string[];
}

export interface ItemDetail extends ItemSummary {
	sort_title: string | null;
	description: string | null;
	publisher: string | null;
	publish_date: string | null;
	language: string;
	isbn: string | null;
	isbn13: string | null;
	tags: string[] | null;
	classification_code: string | null;
	page_count: number | null;
	creators: Creator[];
	files: FileInfo[];
	date_added: string;
}

export interface Creator {
	id: number;
	name: string;
	role: string;
}

export interface FileInfo {
	id: number;
	format: string;
	size_bytes: number | null;
}

export interface AuthorSummary {
	id: number;
	name: string;
	sort_name: string | null;
	book_count: number;
}

export interface AuthorDetail {
	id: number;
	name: string;
	sort_name: string | null;
	bio: string | null;
	photo_url: string | null;
}

export interface SeriesSummary {
	name: string;
	book_count: number;
	authors: string[];
	first_cover_url: string | null;
}

export interface SeriesDetail {
	name: string;
	books: ItemSummary[];
	authors: string[];
}

export interface PaginatedSeries {
	series: SeriesSummary[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export interface PaginatedItems {
	items: ItemSummary[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export interface PaginatedAuthors {
	authors: AuthorSummary[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export interface LibraryStats {
	total_items: number;
	total_files: number;
	total_authors: number;
	total_series: number;
	total_size_bytes: number;
	formats: Record<string, number>;
	media_types: Record<string, number>;
	migration_status: Record<string, number> | null;
}

// Type for SvelteKit's fetch function
type FetchFunction = typeof fetch;

async function fetchJson<T>(url: string, customFetch?: FetchFunction): Promise<T> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(url);
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function getRecentItems(limit = 12, customFetch?: FetchFunction): Promise<ItemSummary[]> {
	return fetchJson<ItemSummary[]>(`${API_BASE}/items/recent?limit=${limit}`, customFetch);
}

export async function getItems(params: {
	page?: number;
	per_page?: number;
	sort?: string;
	order?: string;
	q?: string;
	author_id?: number;
	series?: string;
	tag?: string;
	format?: string;
	media_type?: string;
} = {}, customFetch?: FetchFunction): Promise<PaginatedItems> {
	const searchParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) {
			searchParams.set(key, String(value));
		}
	}
	return fetchJson<PaginatedItems>(`${API_BASE}/items?${searchParams}`, customFetch);
}

export async function getItem(id: number, customFetch?: FetchFunction): Promise<ItemDetail> {
	return fetchJson<ItemDetail>(`${API_BASE}/items/${id}`, customFetch);
}

export async function getAuthors(params: {
	page?: number;
	per_page?: number;
	q?: string;
	sort?: string;
	order?: string;
} = {}, customFetch?: FetchFunction): Promise<PaginatedAuthors> {
	const searchParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) {
			searchParams.set(key, String(value));
		}
	}
	return fetchJson<PaginatedAuthors>(`${API_BASE}/authors?${searchParams}`, customFetch);
}

export async function getStats(customFetch?: FetchFunction): Promise<LibraryStats> {
	return fetchJson<LibraryStats>(`${API_BASE}/stats`, customFetch);
}

export async function getAuthor(id: number, customFetch?: FetchFunction): Promise<AuthorDetail> {
	return fetchJson<AuthorDetail>(`${API_BASE}/authors/${id}`, customFetch);
}

export async function getSeries(params: {
	page?: number;
	per_page?: number;
	q?: string;
	sort?: string;
	order?: string;
} = {}, customFetch?: FetchFunction): Promise<PaginatedSeries> {
	const searchParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) {
			searchParams.set(key, String(value));
		}
	}
	return fetchJson<PaginatedSeries>(`${API_BASE}/series?${searchParams}`, customFetch);
}

export async function getSeriesDetail(name: string, customFetch?: FetchFunction): Promise<SeriesDetail> {
	return fetchJson<SeriesDetail>(`${API_BASE}/series/${encodeURIComponent(name)}`, customFetch);
}

export function formatBytes(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
	return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

// =============================================================================
// Item editing
// =============================================================================

export interface ItemUpdate {
	title?: string;
	subtitle?: string;
	description?: string;
	publisher?: string;
	isbn?: string;
	isbn13?: string;
	series_name?: string;
	series_index?: number;
	classification_code?: string;
	tags?: string[];
}

export interface RefileRequest {
	target_category?: 'fiction' | 'non-fiction';
	target_ddc?: string;
}

export interface AuthorFixRequest {
	creator_id: number;
	corrected_name: string;
}

export interface EditRequest {
	id: number;
	item_id: number;
	request_type: string;
	request_data: Record<string, unknown>;
	status: string;
	error_message: string | null;
	created_at: string;
	processed_at: string | null;
}

export interface SetCoverResponse {
	success: boolean;
	cover_url: string | null;
}

export async function updateItem(
	id: number,
	updates: ItemUpdate,
	customFetch?: FetchFunction
): Promise<ItemDetail> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updates)
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function requestRefile(
	itemId: number,
	request: RefileRequest,
	customFetch?: FetchFunction
): Promise<EditRequest> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/refile`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function requestAuthorFix(
	itemId: number,
	request: AuthorFixRequest,
	customFetch?: FetchFunction
): Promise<EditRequest> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/fix-author`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function getItemEditRequests(
	itemId: number,
	customFetch?: FetchFunction
): Promise<{ requests: EditRequest[]; total: number }> {
	return fetchJson(`${API_BASE}/items/${itemId}/edit-requests`, customFetch);
}

export async function removeCreator(
	itemId: number,
	creatorId: number,
	customFetch?: FetchFunction
): Promise<ItemDetail> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/creators/${creatorId}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

/**
 * Set item cover from a URL.
 */
export async function setItemCover(
	itemId: number,
	url: string,
	customFetch?: FetchFunction
): Promise<SetCoverResponse> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/cover`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ url })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

/**
 * Upload a cover image file.
 */
export async function uploadItemCover(
	itemId: number,
	file: File,
	customFetch?: FetchFunction
): Promise<SetCoverResponse> {
	const fetchFn = customFetch ?? fetch;
	const formData = new FormData();
	formData.append('file', file);

	const response = await fetchFn(`${API_BASE}/items/${itemId}/cover/upload`, {
		method: 'POST',
		body: formData
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

// =============================================================================
// Item enrichment (for improving existing item metadata)
// =============================================================================

export interface ItemEnrichedResult {
	found: boolean;
	title: string | null;
	authors: string[];
	ddc: string | null;
	subjects: string[];
	publisher: string | null;
	publish_date: string | null;
	description: string | null;
	isbn: string | null;
	isbn13: string | null;
	cover_url: string | null;
	series: string | null;
	series_number: number | null;
}

export interface ItemSearchCandidate {
	source: string;
	title: string | null;
	authors: string[];
	publisher: string | null;
	publish_date: string | null;
	description: string | null;
	isbn: string | null;
	isbn13: string | null;
	cover_url: string | null;
	ddc: string | null;
	series: string | null;
	series_number: number | null;
}

export interface ItemSearchCandidatesResponse {
	candidates: ItemSearchCandidate[];
	query_title: string;
	query_author: string | null;
}

/**
 * Search for metadata by ISBN to enrich an existing item.
 */
export async function enrichItemByIsbn(
	itemId: number,
	isbn: string,
	customFetch?: FetchFunction
): Promise<ItemEnrichedResult> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/enrich/isbn`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ isbn })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

/**
 * Search for metadata by title/author to enrich an existing item.
 */
export async function enrichItemByTitle(
	itemId: number,
	title: string,
	author?: string,
	customFetch?: FetchFunction
): Promise<ItemEnrichedResult> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/enrich/title`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title, author })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

/**
 * Search for books by title/author, returning multiple candidates for user selection.
 */
export async function searchItemByTitle(
	itemId: number,
	title: string,
	author?: string,
	customFetch?: FetchFunction
): Promise<ItemSearchCandidatesResponse> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/items/${itemId}/search/title`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title, author })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

// =============================================================================
// Piles (Collections)
// =============================================================================

export interface PileSummary {
	id: number;
	name: string;
	description: string | null;
	item_count: number;
	first_cover_url: string | null;
}

export interface PileDetail {
	id: number;
	name: string;
	description: string | null;
	items: ItemSummary[];
}

export interface PileList {
	piles: PileSummary[];
	total: number;
}

export async function getPiles(customFetch?: FetchFunction): Promise<PileList> {
	return fetchJson<PileList>(`${API_BASE}/piles`, customFetch);
}

export async function getPile(id: number, customFetch?: FetchFunction): Promise<PileDetail> {
	return fetchJson<PileDetail>(`${API_BASE}/piles/${id}`, customFetch);
}

export async function createPile(
	name: string,
	description?: string,
	customFetch?: FetchFunction
): Promise<PileSummary> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/piles`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, description })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function updatePile(
	id: number,
	updates: { name?: string; description?: string },
	customFetch?: FetchFunction
): Promise<PileSummary> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/piles/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updates)
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function deletePile(id: number, customFetch?: FetchFunction): Promise<void> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/piles/${id}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
}

export async function addItemsToPile(
	pileId: number,
	itemIds: number[],
	customFetch?: FetchFunction
): Promise<{ added: number }> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/piles/${pileId}/items`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ item_ids: itemIds })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function removeItemsFromPile(
	pileId: number,
	itemIds: number[],
	customFetch?: FetchFunction
): Promise<{ removed: number }> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/piles/${pileId}/items`, {
		method: 'DELETE',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ item_ids: itemIds })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function getPilesForItem(
	itemId: number,
	customFetch?: FetchFunction
): Promise<PileSummary[]> {
	return fetchJson<PileSummary[]>(`${API_BASE}/piles/for-item/${itemId}`, customFetch);
}

// =============================================================================
// Review (Source Files)
// =============================================================================

export interface SourceFile {
	id: number;
	filename: string;
	source_path: string;
	format: string;
	size_bytes: number;
	status: string;
	title: string | null;
	authors: string[];
	isbn: string | null;
	series: string | null;
	series_index: number | null;
	enriched_title: string | null;
	enriched_authors: string[];
	enriched_ddc: string | null;
	enriched_subjects: string[];
	classification_ddc: string | null;
	classification_confidence: number | null;
}

export interface ReviewList {
	items: SourceFile[];
	total: number;
	pending: number;
	skip: number;
	limit: number;
}

export interface ReviewStats {
	by_status: Record<string, number>;
	pending_by_format: Record<string, number>;
}

export interface EnrichedResult {
	found: boolean;
	title: string | null;
	authors: string[];
	ddc: string | null;
	subjects: string[];
	publisher: string | null;
	publish_date: string | null;
	description: string | null;
	isbn: string | null;
	isbn13: string | null;
	cover_url: string | null;
	series: string | null;
	series_number: number | null;
}

export interface FileResult {
	success: boolean;
	item_id: number | null;
	item_title: string | null;
	error: string | null;
	was_duplicate: boolean;
	duplicate_of_id: number | null;
	duplicate_of_title: string | null;
}

export interface PotentialDuplicate {
	item_id: number;
	title: string;
	authors: string[];
	match_reason: 'isbn' | 'title_author' | 'title';
}

export interface DuplicateCheckResponse {
	has_potential_duplicates: boolean;
	duplicates: PotentialDuplicate[];
}

export async function getReviewQueue(
	params: { skip?: number; limit?: number; format?: string; status?: string } = {},
	customFetch?: FetchFunction
): Promise<ReviewList> {
	const searchParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) {
			searchParams.set(key, String(value));
		}
	}
	return fetchJson<ReviewList>(`${API_BASE}/review?${searchParams}`, customFetch);
}

export async function getReviewStats(customFetch?: FetchFunction): Promise<ReviewStats> {
	return fetchJson<ReviewStats>(`${API_BASE}/review/stats`, customFetch);
}

export async function getSourceFile(id: number, customFetch?: FetchFunction): Promise<SourceFile> {
	return fetchJson<SourceFile>(`${API_BASE}/review/${id}`, customFetch);
}

export async function enrichByIsbn(
	sourceFileId: number,
	isbn: string,
	customFetch?: FetchFunction
): Promise<EnrichedResult> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/review/${sourceFileId}/enrich/isbn`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ isbn })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function enrichByTitle(
	sourceFileId: number,
	title: string,
	author?: string,
	customFetch?: FetchFunction
): Promise<EnrichedResult> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/review/${sourceFileId}/enrich/title`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title, author })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function checkDuplicates(
	sourceFileId: number,
	customFetch?: FetchFunction
): Promise<DuplicateCheckResponse> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/review/${sourceFileId}/duplicates`);
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export interface FileSourceOptions {
	use_enrichment?: boolean;
	force_ddc?: string;
	force_fiction?: boolean;
	// Manually edited metadata fields
	edited_title?: string;
	edited_authors?: string[];
	edited_isbn?: string;
	edited_publisher?: string;
	edited_publish_date?: string;
	edited_series?: string;
	edited_series_index?: number;
	edited_description?: string;
}

export async function fileSourceFile(
	sourceFileId: number,
	options: FileSourceOptions = {},
	customFetch?: FetchFunction
): Promise<FileResult> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/review/${sourceFileId}/file`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(options)
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

export async function skipSourceFile(
	sourceFileId: number,
	status: 'skipped' | 'duplicate' = 'skipped',
	customFetch?: FetchFunction
): Promise<{ success: boolean; status: string }> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/review/${sourceFileId}/skip`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ status })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}

// =============================================================================
// Multi-result Title Search
// =============================================================================

export interface SearchCandidate {
	source: 'google_books' | 'openlibrary';
	title: string | null;
	authors: string[];
	publisher: string | null;
	publish_date: string | null;
	description: string | null;
	isbn: string | null;
	isbn13: string | null;
	cover_url: string | null;
	ddc: string | null;
	series: string | null;
	series_number: number | null;
}

export interface SearchCandidatesResponse {
	candidates: SearchCandidate[];
	query_title: string;
	query_author: string | null;
}

export async function searchByTitle(
	sourceFileId: number,
	title: string,
	author?: string,
	customFetch?: FetchFunction
): Promise<SearchCandidatesResponse> {
	const fetchFn = customFetch ?? fetch;
	const response = await fetchFn(`${API_BASE}/review/${sourceFileId}/search/title`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title, author })
	});
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	return response.json();
}
