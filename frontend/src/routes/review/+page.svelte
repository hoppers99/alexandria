<script lang="ts">
	import {
		formatBytes,
		enrichByIsbn,
		enrichByTitle,
		searchByTitle,
		fileSourceFile,
		skipSourceFile,
		getAuthors,
		getSeries,
		checkDuplicates,
		type SourceFile,
		type ReviewList,
		type ReviewStats,
		type EnrichedResult,
		type AuthorSummary,
		type SeriesSummary,
		type FileSourceOptions,
		type PotentialDuplicate,
		type SearchCandidate
	} from '$lib/api';
	import { goto, invalidateAll } from '$app/navigation';

	interface Props {
		data: {
			queue: ReviewList;
			stats: ReviewStats;
			currentSkip: number;
			currentFormat: string | undefined;
		};
	}

	let { data }: Props = $props();

	// Current source file being reviewed
	let currentFile = $derived(data.queue.items[0] || null);

	// UI state
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Search state
	let showIsbnSearch = $state(false);
	let showTitleSearch = $state(false);
	let searchIsbn = $state('');
	let searchTitle = $state('');
	let searchAuthor = $state('');
	let searchResult = $state<EnrichedResult | null>(null);
	let searchCandidates = $state<SearchCandidate[]>([]);
	let isSearching = $state(false);

	// Lightbox state
	let lightboxImage = $state<string | null>(null);
	let lightboxTitle = $state<string>('');

	// Editable enriched metadata
	let editTitle = $state('');
	let editAuthors = $state<string[]>([]);
	let editIsbn = $state('');
	let editPublisher = $state('');
	let editPublishDate = $state('');
	let editSeries = $state('');
	let editSeriesIndex = $state('');
	let editDdc = $state('');
	let editDescription = $state('');
	let editCoverUrl = $state<string | null>(null);

	// Author/Series autocomplete state
	let authorQuery = $state('');
	let authorSuggestions = $state<AuthorSummary[]>([]);
	let showAuthorSuggestions = $state(false);
	let seriesQuery = $state('');
	let seriesSuggestions = $state<SeriesSummary[]>([]);
	let showSeriesSuggestions = $state(false);

	// Duplicate detection state
	let potentialDuplicates = $state<PotentialDuplicate[]>([]);
	let isCheckingDuplicates = $state(false);

	// Check for duplicates when file changes
	$effect(() => {
		if (currentFile) {
			checkForDuplicates(currentFile.id);
		}
	});

	async function checkForDuplicates(fileId: number) {
		isCheckingDuplicates = true;
		potentialDuplicates = [];
		try {
			const result = await checkDuplicates(fileId);
			potentialDuplicates = result.duplicates;
		} catch {
			// Silently fail - duplicates are a hint, not critical
			potentialDuplicates = [];
		} finally {
			isCheckingDuplicates = false;
		}
	}

	// Initialize editable fields from current file
	$effect(() => {
		if (currentFile) {
			// Start with extracted metadata, prefer any existing enriched data
			editTitle = currentFile.enriched_title || currentFile.title || '';
			editAuthors = currentFile.enriched_authors?.length
				? [...currentFile.enriched_authors]
				: currentFile.authors?.length
					? [...currentFile.authors]
					: [];
			editIsbn = currentFile.isbn || '';
			editSeries = currentFile.series || '';
			editSeriesIndex = currentFile.series_index?.toString() || '';
			editDdc = currentFile.enriched_ddc || currentFile.classification_ddc || '';
			editPublisher = '';
			editPublishDate = '';
			editDescription = '';
			editCoverUrl = null;

			// Also initialize search fields
			searchIsbn = currentFile.isbn || '';
			searchTitle = currentFile.enriched_title || currentFile.title || '';
			searchAuthor = currentFile.enriched_authors?.[0] || currentFile.authors?.[0] || '';
		}
	});

	// Search authors for autocomplete
	async function searchAuthors(query: string) {
		if (query.length < 2) {
			authorSuggestions = [];
			return;
		}
		try {
			const result = await getAuthors({ q: query, per_page: 10 });
			authorSuggestions = result.authors;
		} catch {
			authorSuggestions = [];
		}
	}

	// Search series for autocomplete
	async function searchSeriesNames(query: string) {
		if (query.length < 2) {
			seriesSuggestions = [];
			return;
		}
		try {
			const result = await getSeries({ q: query, per_page: 10 });
			seriesSuggestions = result.series;
		} catch {
			seriesSuggestions = [];
		}
	}

	function addAuthor(name: string) {
		if (name && !editAuthors.includes(name)) {
			editAuthors = [...editAuthors, name];
		}
		authorQuery = '';
		showAuthorSuggestions = false;
	}

	function removeAuthor(index: number) {
		editAuthors = editAuthors.filter((_, i) => i !== index);
	}

	function selectSeries(name: string) {
		editSeries = name;
		seriesQuery = '';
		showSeriesSuggestions = false;
	}

	// Apply search result to edit fields - merging, not replacing
	function applySearchResult() {
		if (!searchResult || !searchResult.found) return;

		// Only fill in fields that are empty or use search data if better
		if (!editTitle && searchResult.title) editTitle = searchResult.title;
		if (editAuthors.length === 0 && searchResult.authors?.length) {
			editAuthors = [...searchResult.authors];
		}
		if (!editIsbn && (searchResult.isbn13 || searchResult.isbn)) {
			editIsbn = searchResult.isbn13 || searchResult.isbn || '';
		}
		if (!editPublisher && searchResult.publisher) editPublisher = searchResult.publisher;
		if (!editPublishDate && searchResult.publish_date) editPublishDate = searchResult.publish_date;
		if (!editSeries && searchResult.series) {
			editSeries = searchResult.series;
			if (searchResult.series_number) editSeriesIndex = searchResult.series_number.toString();
		}
		if (!editDdc && searchResult.ddc) editDdc = searchResult.ddc;
		if (!editDescription && searchResult.description) editDescription = searchResult.description;
		if (!editCoverUrl && searchResult.cover_url) editCoverUrl = searchResult.cover_url;

		// Close search result panel after applying
		searchResult = null;
	}

	// Replace all edit fields with search result data
	function replaceWithSearchResult() {
		if (!searchResult || !searchResult.found) return;

		if (searchResult.title) editTitle = searchResult.title;
		if (searchResult.authors?.length) editAuthors = [...searchResult.authors];
		if (searchResult.isbn13 || searchResult.isbn) editIsbn = searchResult.isbn13 || searchResult.isbn || '';
		if (searchResult.publisher) editPublisher = searchResult.publisher;
		if (searchResult.publish_date) editPublishDate = searchResult.publish_date;
		if (searchResult.series) {
			editSeries = searchResult.series;
			if (searchResult.series_number) editSeriesIndex = searchResult.series_number.toString();
		}
		if (searchResult.ddc) editDdc = searchResult.ddc;
		if (searchResult.description) editDescription = searchResult.description;
		if (searchResult.cover_url) editCoverUrl = searchResult.cover_url;

		// Close search result panel after applying
		searchResult = null;
	}

	function clearMessages() {
		error = null;
		success = null;
	}

	async function handleSkip() {
		// Clear search state for next file
		searchResult = null;
		searchCandidates = [];
		showIsbnSearch = false;
		showTitleSearch = false;
		// Navigate to next file
		const nextSkip = data.currentSkip + 1;
		await goto(`/review?skip=${nextSkip}${data.currentFormat ? `&format=${data.currentFormat}` : ''}`);
	}

	async function handleSearchIsbn() {
		if (!currentFile || !searchIsbn.trim()) return;

		clearMessages();
		isSearching = true;
		searchResult = null;

		try {
			const result = await enrichByIsbn(currentFile.id, searchIsbn.trim());
			searchResult = result;

			if (!result.found) {
				error = 'No results found for that ISBN';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	async function handleSearchTitle() {
		if (!currentFile || !searchTitle.trim()) return;

		clearMessages();
		isSearching = true;
		searchResult = null;
		searchCandidates = [];

		try {
			const result = await searchByTitle(
				currentFile.id,
				searchTitle.trim(),
				searchAuthor.trim() || undefined
			);
			searchCandidates = result.candidates;

			if (result.candidates.length === 0) {
				error = 'No results found';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	// Apply a search candidate to the edit fields
	function applyCandidate(candidate: SearchCandidate) {
		if (candidate.title) editTitle = candidate.title;
		if (candidate.authors?.length) editAuthors = [...candidate.authors];
		if (candidate.isbn13 || candidate.isbn) editIsbn = candidate.isbn13 || candidate.isbn || '';
		if (candidate.publisher) editPublisher = candidate.publisher;
		if (candidate.publish_date) editPublishDate = candidate.publish_date;
		if (candidate.series) {
			editSeries = candidate.series;
			if (candidate.series_number) editSeriesIndex = candidate.series_number.toString();
		}
		if (candidate.ddc) editDdc = candidate.ddc;
		if (candidate.description) editDescription = candidate.description;
		if (candidate.cover_url) editCoverUrl = candidate.cover_url;

		// Clear candidates after selecting
		searchCandidates = [];
	}

	async function handleFile() {
		if (!currentFile) return;

		// Validate we have at least a title
		if (!editTitle.trim()) {
			error = 'Title is required to file';
			return;
		}

		clearMessages();
		isLoading = true;

		try {
			// Build options with edited metadata
			const options: FileSourceOptions = {
				edited_title: editTitle.trim(),
				edited_authors: editAuthors.filter((a) => a.trim()),
				edited_isbn: editIsbn.trim() || undefined,
				edited_publisher: editPublisher.trim() || undefined,
				edited_publish_date: editPublishDate.trim() || undefined,
				edited_series: editSeries.trim() || undefined,
				edited_series_index: editSeriesIndex ? parseFloat(editSeriesIndex) : undefined,
				edited_description: editDescription.trim() || undefined,
				force_ddc: editDdc.trim() || undefined
			};

			const result = await fileSourceFile(currentFile.id, options);

			if (result.success) {
				if (result.was_duplicate) {
					success = `Marked as duplicate of: "${result.duplicate_of_title}"`;
				} else {
					success = `Filed as: ${result.item_title}`;
				}
				// Clear search state for next file
				searchResult = null;
				searchCandidates = [];
				showIsbnSearch = false;
				showTitleSearch = false;
				potentialDuplicates = [];
				// Move to next file after a short delay
				setTimeout(() => {
					goto(`/review?skip=${data.currentSkip}${data.currentFormat ? `&format=${data.currentFormat}` : ''}`);
				}, 1000);
			} else {
				error = result.error || 'Filing failed';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Filing failed';
		} finally {
			isLoading = false;
		}
	}

	async function handleMarkSkipped(status: 'skipped' | 'duplicate') {
		if (!currentFile) return;

		clearMessages();
		isLoading = true;

		try {
			await skipSourceFile(currentFile.id, status);
			success = `Marked as ${status}`;
			// Clear search state for next file
			searchResult = null;
			searchCandidates = [];
			showIsbnSearch = false;
			showTitleSearch = false;
			// Move to next file after a short delay
			setTimeout(() => {
				goto(`/review?skip=${data.currentSkip}${data.currentFormat ? `&format=${data.currentFormat}` : ''}`);
			}, 500);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to skip';
		} finally {
			isLoading = false;
		}
	}

	function setFormatFilter(format: string | null) {
		if (format) {
			goto(`/review?format=${format}`);
		} else {
			goto('/review');
		}
	}
</script>

<svelte:head>
	<title>Review Queue - Alexandria</title>
</svelte:head>

<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header with stats -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Review Queue</h1>

		<div class="flex flex-wrap gap-4 mb-4">
			<div class="bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
				<span class="text-2xl font-bold text-blue-600">{data.stats.by_status.pending || 0}</span>
				<span class="text-gray-500 dark:text-gray-400 ml-2">pending</span>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
				<span class="text-2xl font-bold text-green-600">{data.stats.by_status.migrated || 0}</span>
				<span class="text-gray-500 dark:text-gray-400 ml-2">migrated</span>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
				<span class="text-2xl font-bold text-yellow-600">{data.stats.by_status.skipped || 0}</span>
				<span class="text-gray-500 dark:text-gray-400 ml-2">skipped</span>
			</div>
		</div>

		<!-- Format filter -->
		<div class="flex flex-wrap gap-2">
			<button
				onclick={() => setFormatFilter(null)}
				class="px-3 py-1 rounded-full text-sm {!data.currentFormat
					? 'bg-blue-600 text-white'
					: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}"
			>
				All
			</button>
			{#each Object.entries(data.stats.pending_by_format) as [format, count]}
				<button
					onclick={() => setFormatFilter(format)}
					class="px-3 py-1 rounded-full text-sm {data.currentFormat === format
						? 'bg-blue-600 text-white'
						: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}"
				>
					{format.toUpperCase()} ({count})
				</button>
			{/each}
		</div>
	</div>

	<!-- Messages -->
	{#if error}
		<div class="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg">
			{error}
		</div>
	{/if}
	{#if success}
		<div class="mb-4 p-3 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg">
			{success}
		</div>
	{/if}

	{#if !currentFile}
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-8 text-center">
			<svg
				class="mx-auto h-12 w-12 text-green-500"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
			<h3 class="mt-2 text-lg font-medium text-gray-900 dark:text-white">No files to review!</h3>
			<p class="mt-1 text-gray-500 dark:text-gray-400">
				{#if data.currentFormat}
					No pending {data.currentFormat.toUpperCase()} files. Try removing the filter.
				{:else}
					All files have been processed.
				{/if}
			</p>
		</div>
	{:else}
		<!-- Current file card -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
			<!-- Progress indicator -->
			<div class="bg-gray-100 dark:bg-gray-700 px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
				Reviewing {data.currentSkip + 1} of {data.queue.pending}
			</div>

			<div class="p-6">
				<!-- File info -->
				<div class="mb-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2 break-all">
						{currentFile.filename}
					</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400 break-all mb-2">
						{currentFile.source_path}
					</p>
					<div class="flex gap-4 text-sm">
						<span class="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-700 dark:text-gray-300">
							{currentFile.format.toUpperCase()}
						</span>
						<span class="text-gray-500 dark:text-gray-400">
							{formatBytes(currentFile.size_bytes)}
						</span>
					</div>
				</div>

				<!-- Duplicate warning -->
				{#if potentialDuplicates.length > 0}
					<div class="mb-6 p-4 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg">
						<div class="flex items-start gap-3">
							<svg class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
							</svg>
							<div class="flex-1">
								<h4 class="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-2">
									Potential Duplicate{potentialDuplicates.length > 1 ? 's' : ''} Found
								</h4>
								<ul class="space-y-2">
									{#each potentialDuplicates as dup}
										<li class="text-sm">
											<a
												href="/book/{dup.item_id}"
												target="_blank"
												class="text-amber-700 dark:text-amber-300 hover:underline font-medium"
											>
												{dup.title}
											</a>
											{#if dup.authors.length > 0}
												<span class="text-amber-600 dark:text-amber-400">
													by {dup.authors.join(', ')}
												</span>
											{/if}
											<span class="text-xs text-amber-500 dark:text-amber-500 ml-2">
												(matched by {dup.match_reason === 'isbn' ? 'ISBN' : dup.match_reason === 'title_author' ? 'title & author' : 'title'})
											</span>
										</li>
									{/each}
								</ul>
								<p class="text-xs text-amber-600 dark:text-amber-400 mt-2">
									If this is a duplicate, use "Mark Duplicate" below. Otherwise, proceed with filing.
								</p>
							</div>
						</div>
					</div>
				{:else if isCheckingDuplicates}
					<div class="mb-6 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm text-gray-500 dark:text-gray-400">
						Checking for duplicates...
					</div>
				{/if}

				<!-- Source file cover preview -->
				<div class="mb-6">
					<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
						Source File Preview
					</h3>
					<div class="flex gap-4 items-start">
						<div class="flex-shrink-0">
							<button
								type="button"
								onclick={() => {
									lightboxImage = `/api/review/${currentFile.id}/cover`;
									lightboxTitle = 'Source File Cover';
								}}
								class="cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
							>
								<img
									src="/api/review/{currentFile.id}/cover"
									alt="Source file cover"
									class="w-32 h-48 object-cover rounded shadow-md bg-gray-200 dark:bg-gray-700 hover:opacity-90 transition-opacity"
									onerror={(e) => {
										const target = e.currentTarget as HTMLImageElement;
										target.parentElement!.style.display = 'none';
										const placeholder = target.parentElement!.nextElementSibling as HTMLElement;
										if (placeholder) placeholder.style.display = 'flex';
									}}
								/>
							</button>
							<div class="w-32 h-48 hidden items-center justify-center bg-gray-200 dark:bg-gray-700 rounded text-gray-400 dark:text-gray-500 text-xs text-center p-2">
								No cover in file
							</div>
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							<p class="mb-2">Cover extracted from the source file.</p>
							<p>Click to enlarge. Compare with search results.</p>
						</div>
					</div>
				</div>

				<!-- Metadata sections -->
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
					<!-- Extracted metadata (read-only reference) -->
					<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
						<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
							Extracted Metadata
						</h3>
						<dl class="space-y-2 text-sm">
							<div>
								<dt class="text-gray-500 dark:text-gray-400">Title</dt>
								<dd class="text-gray-900 dark:text-white">{currentFile.title || '[none]'}</dd>
							</div>
							<div>
								<dt class="text-gray-500 dark:text-gray-400">Authors</dt>
								<dd class="text-gray-900 dark:text-white">
									{currentFile.authors?.join(', ') || '[none]'}
								</dd>
							</div>
							<div>
								<dt class="text-gray-500 dark:text-gray-400">ISBN</dt>
								<dd class="text-gray-900 dark:text-white font-mono">
									{currentFile.isbn || '[none]'}
								</dd>
							</div>
							{#if currentFile.series}
								<div>
									<dt class="text-gray-500 dark:text-gray-400">Series</dt>
									<dd class="text-gray-900 dark:text-white">
										{currentFile.series} #{currentFile.series_index || '?'}
									</dd>
								</div>
							{/if}
						</dl>
					</div>

					<!-- Editable enriched metadata form -->
					<div class="lg:col-span-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
						<h3 class="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-3">
							Filing Metadata (editable)
						</h3>
						<div class="space-y-3">
							<!-- Title -->
							<div>
								<label for="edit-title" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
									Title
								</label>
								<input
									id="edit-title"
									type="text"
									bind:value={editTitle}
									class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									placeholder="Enter title..."
								/>
							</div>

							<!-- Authors with autocomplete -->
							<div>
								<span class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
									Authors
								</span>
								<!-- Current authors -->
								<div class="flex flex-wrap gap-1 mb-2">
									{#each editAuthors as author, i}
										<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 rounded text-xs">
											{author}
											<button
												type="button"
												onclick={() => removeAuthor(i)}
												class="hover:text-red-600 dark:hover:text-red-400"
												aria-label="Remove {author}"
											>
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
												</svg>
											</button>
										</span>
									{/each}
								</div>
								<!-- Add author input -->
								<div class="relative">
									<input
										type="text"
										bind:value={authorQuery}
										oninput={() => {
											searchAuthors(authorQuery);
											showAuthorSuggestions = true;
										}}
										onfocus={() => {
											if (authorQuery.length >= 2) showAuthorSuggestions = true;
										}}
										onblur={() => setTimeout(() => (showAuthorSuggestions = false), 200)}
										onkeydown={(e) => {
											if (e.key === 'Enter' && authorQuery.trim()) {
												e.preventDefault();
												addAuthor(authorQuery.trim());
											}
										}}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="Type to search or add author..."
									/>
									{#if showAuthorSuggestions && authorSuggestions.length > 0}
										<div class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-40 overflow-y-auto">
											{#each authorSuggestions as suggestion}
												<button
													type="button"
													onclick={() => addAuthor(suggestion.name)}
													class="w-full px-3 py-2 text-left text-sm hover:bg-blue-50 dark:hover:bg-blue-900/50 text-gray-900 dark:text-white"
												>
													{suggestion.name}
													<span class="text-xs text-gray-500 dark:text-gray-400 ml-2">
														({suggestion.book_count} books)
													</span>
												</button>
											{/each}
										</div>
									{/if}
								</div>
							</div>

							<!-- ISBN and DDC in row -->
							<div class="grid grid-cols-2 gap-3">
								<div>
									<label for="edit-isbn" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
										ISBN
									</label>
									<input
										id="edit-isbn"
										type="text"
										bind:value={editIsbn}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="ISBN..."
									/>
								</div>
								<div>
									<label for="edit-ddc" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
										DDC Classification
									</label>
									<input
										id="edit-ddc"
										type="text"
										bind:value={editDdc}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="e.g. 813.54"
									/>
								</div>
							</div>

							<!-- Series with autocomplete -->
							<div class="grid grid-cols-3 gap-3">
								<div class="col-span-2 relative">
									<label for="edit-series" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
										Series
									</label>
									<input
										id="edit-series"
										type="text"
										bind:value={editSeries}
										oninput={() => {
											seriesQuery = editSeries;
											searchSeriesNames(editSeries);
											showSeriesSuggestions = true;
										}}
										onfocus={() => {
											if (editSeries.length >= 2) {
												seriesQuery = editSeries;
												searchSeriesNames(editSeries);
												showSeriesSuggestions = true;
											}
										}}
										onblur={() => setTimeout(() => (showSeriesSuggestions = false), 200)}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="Series name..."
									/>
									{#if showSeriesSuggestions && seriesSuggestions.length > 0}
										<div class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-40 overflow-y-auto">
											{#each seriesSuggestions as suggestion}
												<button
													type="button"
													onclick={() => selectSeries(suggestion.name)}
													class="w-full px-3 py-2 text-left text-sm hover:bg-blue-50 dark:hover:bg-blue-900/50 text-gray-900 dark:text-white"
												>
													{suggestion.name}
													<span class="text-xs text-gray-500 dark:text-gray-400 ml-2">
														({suggestion.book_count} books)
													</span>
												</button>
											{/each}
										</div>
									{/if}
								</div>
								<div>
									<label for="edit-series-index" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
										# in Series
									</label>
									<input
										id="edit-series-index"
										type="text"
										bind:value={editSeriesIndex}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="1"
									/>
								</div>
							</div>

							<!-- Publisher and date -->
							<div class="grid grid-cols-2 gap-3">
								<div>
									<label for="edit-publisher" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
										Publisher
									</label>
									<input
										id="edit-publisher"
										type="text"
										bind:value={editPublisher}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="Publisher..."
									/>
								</div>
								<div>
									<label for="edit-publish-date" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
										Publish Date
									</label>
									<input
										id="edit-publish-date"
										type="text"
										bind:value={editPublishDate}
										class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										placeholder="Year or date..."
									/>
								</div>
							</div>

							<!-- Description -->
							<div>
								<label for="edit-description" class="block text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
									Description
								</label>
								<textarea
									id="edit-description"
									bind:value={editDescription}
									rows="3"
									class="w-full px-3 py-1.5 text-sm border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
									placeholder="Book description..."
								></textarea>
							</div>
						</div>
					</div>
				</div>

				<!-- Search panels -->
				<div class="border-t border-gray-200 dark:border-gray-700 pt-6 mb-6">
					<div class="flex gap-2 mb-4">
						<button
							onclick={() => {
								showIsbnSearch = !showIsbnSearch;
								showTitleSearch = false;
							}}
							class="px-3 py-2 text-sm rounded-lg {showIsbnSearch
								? 'bg-blue-600 text-white'
								: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
						>
							Search by ISBN
						</button>
						<button
							onclick={() => {
								showTitleSearch = !showTitleSearch;
								showIsbnSearch = false;
							}}
							class="px-3 py-2 text-sm rounded-lg {showTitleSearch
								? 'bg-blue-600 text-white'
								: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
						>
							Search by Title
						</button>
					</div>

					{#if showIsbnSearch}
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
							<div class="flex gap-2">
								<input
									type="text"
									bind:value={searchIsbn}
									placeholder="Enter ISBN..."
									class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								/>
								<button
									onclick={handleSearchIsbn}
									disabled={isSearching || !searchIsbn.trim()}
									class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
								>
									{isSearching ? 'Searching...' : 'Search'}
								</button>
							</div>
						</div>
					{/if}

					{#if showTitleSearch}
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3">
							<input
								type="text"
								bind:value={searchTitle}
								placeholder="Title..."
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							/>
							<div class="flex gap-2">
								<input
									type="text"
									bind:value={searchAuthor}
									placeholder="Author (optional)..."
									class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								/>
								<button
									onclick={handleSearchTitle}
									disabled={isSearching || !searchTitle.trim()}
									class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
								>
									{isSearching ? 'Searching...' : 'Search'}
								</button>
							</div>
						</div>
					{/if}

					<!-- Multiple Search Candidates Display (from title search) -->
					{#if searchCandidates.length > 0}
						<div class="mt-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
							<div class="flex items-center justify-between mb-3">
								<h4 class="text-sm font-semibold text-blue-800 dark:text-blue-200">
									{searchCandidates.length} Results Found - Select One
								</h4>
								<button
									onclick={() => (searchCandidates = [])}
									class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
									aria-label="Dismiss"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>

							<div class="space-y-3 max-h-96 overflow-y-auto">
								{#each searchCandidates as candidate, index}
									<div class="bg-white dark:bg-gray-800 border border-blue-100 dark:border-blue-700 rounded-lg p-3 hover:border-blue-300 dark:hover:border-blue-500 transition-colors">
										<div class="flex gap-3">
											<!-- Cover thumbnail -->
											{#if candidate.cover_url}
												<button
													type="button"
													onclick={() => {
														lightboxImage = candidate.cover_url;
														lightboxTitle = candidate.title || 'Cover';
													}}
													class="flex-shrink-0 cursor-zoom-in"
												>
													<img
														src={candidate.cover_url}
														alt="Cover"
														class="w-16 h-24 object-cover rounded shadow-sm hover:opacity-80 transition-opacity"
													/>
												</button>
											{:else}
												<div class="w-16 h-24 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center text-gray-400 text-xs flex-shrink-0">
													No cover
												</div>
											{/if}

											<!-- Candidate details -->
											<div class="flex-1 min-w-0">
												<div class="flex items-start justify-between gap-2">
													<div class="min-w-0">
														<h5 class="font-medium text-gray-900 dark:text-white truncate">
															{candidate.title || '[No title]'}
														</h5>
														<p class="text-sm text-gray-600 dark:text-gray-400 truncate">
															{candidate.authors?.join(', ') || '[No authors]'}
														</p>
													</div>
													<span class="text-xs px-2 py-0.5 rounded-full flex-shrink-0 {candidate.source === 'google_books' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'}">
														{candidate.source === 'google_books' ? 'Google' : 'Open Library'}
													</span>
												</div>

												<div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
													{#if candidate.publish_date}
														<span>{candidate.publish_date}</span>
													{/if}
													{#if candidate.publisher}
														<span class="truncate max-w-32">{candidate.publisher}</span>
													{/if}
													{#if candidate.isbn13 || candidate.isbn}
														<span class="font-mono">{candidate.isbn13 || candidate.isbn}</span>
													{/if}
													{#if candidate.ddc}
														<span class="font-mono text-purple-600 dark:text-purple-400">DDC: {candidate.ddc}</span>
													{/if}
												</div>

												{#if candidate.description}
													<p class="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
														{candidate.description}
													</p>
												{/if}
											</div>

											<!-- Select button -->
											<button
												onclick={() => applyCandidate(candidate)}
												class="flex-shrink-0 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 font-medium self-center"
											>
												Use
											</button>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Search Result Display (from ISBN search - single result) -->
					{#if searchResult && searchResult.found}
						<div class="mt-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
							<div class="flex items-start justify-between mb-3">
								<h4 class="text-sm font-semibold text-green-800 dark:text-green-200">
									Match Found - Apply to Filing Metadata?
								</h4>
								<button
									onclick={() => (searchResult = null)}
									class="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200"
									aria-label="Dismiss"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>

							<div class="flex gap-4 mb-4">
								<!-- Cover image from search result -->
								{#if searchResult.cover_url}
									<div class="flex-shrink-0">
										<button
											type="button"
											onclick={() => {
												lightboxImage = searchResult!.cover_url;
												lightboxTitle = 'Search Result Cover';
											}}
											class="cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-green-500 rounded"
										>
											<img
												src={searchResult.cover_url}
												alt="Cover"
												class="w-24 h-36 object-cover rounded shadow-md hover:opacity-90 transition-opacity"
											/>
										</button>
									</div>
								{/if}

								<!-- Metadata -->
								<dl class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
									<div>
										<dt class="text-green-700 dark:text-green-300 font-medium">Title</dt>
										<dd class="text-gray-900 dark:text-white">{searchResult.title || '[none]'}</dd>
									</div>
									<div>
										<dt class="text-green-700 dark:text-green-300 font-medium">Authors</dt>
										<dd class="text-gray-900 dark:text-white">{searchResult.authors?.join(', ') || '[none]'}</dd>
									</div>
									{#if searchResult.series}
										<div>
											<dt class="text-green-700 dark:text-green-300 font-medium">Series</dt>
											<dd class="text-gray-900 dark:text-white">
												{searchResult.series}{#if searchResult.series_number} #{searchResult.series_number}{/if}
											</dd>
										</div>
									{/if}
									{#if searchResult.isbn13 || searchResult.isbn}
										<div>
											<dt class="text-green-700 dark:text-green-300 font-medium">ISBN</dt>
											<dd class="text-gray-900 dark:text-white font-mono">{searchResult.isbn13 || searchResult.isbn}</dd>
										</div>
									{/if}
									{#if searchResult.publisher}
										<div>
											<dt class="text-green-700 dark:text-green-300 font-medium">Publisher</dt>
											<dd class="text-gray-900 dark:text-white">{searchResult.publisher}</dd>
										</div>
									{/if}
									{#if searchResult.publish_date}
										<div>
											<dt class="text-green-700 dark:text-green-300 font-medium">Published</dt>
											<dd class="text-gray-900 dark:text-white">{searchResult.publish_date}</dd>
										</div>
									{/if}
									{#if searchResult.ddc}
										<div>
											<dt class="text-green-700 dark:text-green-300 font-medium">DDC Classification</dt>
											<dd class="text-gray-900 dark:text-white font-mono">{searchResult.ddc}</dd>
										</div>
									{/if}
									{#if searchResult.subjects && searchResult.subjects.length > 0}
										<div class="md:col-span-2">
											<dt class="text-green-700 dark:text-green-300 font-medium">Subjects</dt>
											<dd class="text-gray-900 dark:text-white text-xs">{searchResult.subjects.slice(0, 5).join(', ')}</dd>
										</div>
									{/if}
									{#if searchResult.description}
										<div class="md:col-span-2">
											<dt class="text-green-700 dark:text-green-300 font-medium">Description</dt>
											<dd class="text-gray-700 dark:text-gray-300 text-xs line-clamp-3">{searchResult.description}</dd>
										</div>
									{/if}
								</dl>
							</div>

							<!-- Action buttons -->
							<div class="flex gap-2 pt-2 border-t border-green-200 dark:border-green-800">
								<button
									onclick={applySearchResult}
									class="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 font-medium"
								>
									Merge (fill gaps)
								</button>
								<button
									onclick={replaceWithSearchResult}
									class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 font-medium"
								>
									Replace all
								</button>
								<button
									onclick={() => (searchResult = null)}
									class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
								>
									Dismiss
								</button>
							</div>
						</div>
					{/if}
				</div>

				<!-- Actions -->
				<div class="flex flex-wrap gap-3">
					<button
						onclick={handleFile}
						disabled={isLoading || !editTitle.trim()}
						class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
					>
						{isLoading ? 'Filing...' : 'File to Library'}
					</button>

					<button
						onclick={handleSkip}
						disabled={isLoading}
						class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
					>
						Skip
					</button>

					<button
						onclick={() => handleMarkSkipped('skipped')}
						disabled={isLoading}
						class="px-4 py-2 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-lg hover:bg-yellow-200 dark:hover:bg-yellow-900/50 disabled:opacity-50"
					>
						Mark Skipped
					</button>

					<button
						onclick={() => handleMarkSkipped('duplicate')}
						disabled={isLoading}
						class="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50"
					>
						Mark Duplicate
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<!-- Lightbox Modal -->
{#if lightboxImage}
	<div
		class="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
		onclick={() => (lightboxImage = null)}
		onkeydown={(e) => e.key === 'Escape' && (lightboxImage = null)}
		role="dialog"
		aria-modal="true"
		aria-label={lightboxTitle}
		tabindex="-1"
	>
		<div class="relative max-w-3xl max-h-[90vh]">
			<!-- Close button -->
			<button
				onclick={() => (lightboxImage = null)}
				class="absolute -top-10 right-0 text-white hover:text-gray-300 p-2"
				aria-label="Close"
			>
				<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>

			<!-- Title -->
			<div class="absolute -top-10 left-0 text-white text-lg font-medium">
				{lightboxTitle}
			</div>

			<!-- Image -->
			<img
				src={lightboxImage}
				alt={lightboxTitle}
				class="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
				onclick={(e) => e.stopPropagation()}
			/>
		</div>
	</div>
{/if}
