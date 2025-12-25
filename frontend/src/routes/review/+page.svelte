<script lang="ts">
	import {
		formatBytes,
		enrichByIsbn,
		searchByTitle,
		fileSourceFile,
		skipSourceFile,
		checkDuplicates,
		type SourceFile,
		type ReviewList,
		type ReviewStats,
		type EnrichedResult,
		type FileSourceOptions,
		type PotentialDuplicate,
		type SearchCandidate
	} from '$lib/api';
	import { goto } from '$app/navigation';
	import { MetadataForm, SearchPanel, Lightbox, type MetadataValues } from '$lib/components';

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

	// Lightbox state
	let lightboxImage = $state<string | null>(null);
	let lightboxTitle = $state<string>('');

	// Editable metadata - managed via MetadataForm component
	let metadataValues = $state<MetadataValues>({
		title: '',
		authors: [],
		isbn: '',
		ddc: '',
		series: '',
		seriesIndex: '',
		publisher: '',
		publishDate: '',
		description: ''
	});

	// Cover URL from search results
	let editCoverUrl = $state<string | null>(null);

	// Duplicate detection state
	let potentialDuplicates = $state<PotentialDuplicate[]>([]);
	let isCheckingDuplicates = $state(false);

	// Reference to SearchPanel for reset
	let searchPanel: { reset: () => void } | undefined = $state();

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
			metadataValues = {
				title: currentFile.enriched_title || currentFile.title || '',
				authors: currentFile.enriched_authors?.length
					? [...currentFile.enriched_authors]
					: currentFile.authors?.length
						? [...currentFile.authors]
						: [],
				isbn: currentFile.isbn || '',
				ddc: currentFile.enriched_ddc || currentFile.classification_ddc || '',
				series: currentFile.series || '',
				seriesIndex: currentFile.series_index?.toString() || '',
				publisher: '',
				publishDate: '',
				description: ''
			};
			editCoverUrl = null;
		}
	});

	// Derived initial search values
	let initialSearchIsbn = $derived(currentFile?.isbn || '');
	let initialSearchTitle = $derived(
		currentFile?.enriched_title || currentFile?.title || ''
	);
	let initialSearchAuthor = $derived(
		currentFile?.enriched_authors?.[0] || currentFile?.authors?.[0] || ''
	);

	function handleMetadataChange(values: MetadataValues) {
		metadataValues = values;
	}

	// Apply search result to edit fields - merging, not replacing
	function handleMergeResult(result: EnrichedResult) {
		if (!result.found) return;

		const newValues = { ...metadataValues };

		// Only fill in fields that are empty
		if (!newValues.title && result.title) newValues.title = result.title;
		if (newValues.authors.length === 0 && result.authors?.length) {
			newValues.authors = [...result.authors];
		}
		if (!newValues.isbn && (result.isbn13 || result.isbn)) {
			newValues.isbn = result.isbn13 || result.isbn || '';
		}
		if (!newValues.publisher && result.publisher) newValues.publisher = result.publisher;
		if (!newValues.publishDate && result.publish_date) newValues.publishDate = result.publish_date;
		if (!newValues.series && result.series) {
			newValues.series = result.series;
			if (result.series_number) newValues.seriesIndex = result.series_number.toString();
		}
		if (!newValues.ddc && result.ddc) newValues.ddc = result.ddc;
		if (!newValues.description && result.description) newValues.description = result.description;
		if (!editCoverUrl && result.cover_url) editCoverUrl = result.cover_url;

		metadataValues = newValues;
	}

	// Replace all edit fields with search result data
	function handleReplaceResult(result: EnrichedResult) {
		if (!result.found) return;

		const newValues = { ...metadataValues };

		if (result.title) newValues.title = result.title;
		if (result.authors?.length) newValues.authors = [...result.authors];
		if (result.isbn13 || result.isbn) newValues.isbn = result.isbn13 || result.isbn || '';
		if (result.publisher) newValues.publisher = result.publisher;
		if (result.publish_date) newValues.publishDate = result.publish_date;
		if (result.series) {
			newValues.series = result.series;
			if (result.series_number) newValues.seriesIndex = result.series_number.toString();
		}
		if (result.ddc) newValues.ddc = result.ddc;
		if (result.description) newValues.description = result.description;
		if (result.cover_url) editCoverUrl = result.cover_url;

		metadataValues = newValues;
	}

	// Apply a search candidate to the edit fields
	function handleSelectCandidate(candidate: SearchCandidate) {
		const newValues = { ...metadataValues };

		if (candidate.title) newValues.title = candidate.title;
		if (candidate.authors?.length) newValues.authors = [...candidate.authors];
		if (candidate.isbn13 || candidate.isbn) newValues.isbn = candidate.isbn13 || candidate.isbn || '';
		if (candidate.publisher) newValues.publisher = candidate.publisher;
		if (candidate.publish_date) newValues.publishDate = candidate.publish_date;
		if (candidate.series) {
			newValues.series = candidate.series;
			if (candidate.series_number) newValues.seriesIndex = candidate.series_number.toString();
		}
		if (candidate.ddc) newValues.ddc = candidate.ddc;
		if (candidate.description) newValues.description = candidate.description;
		if (candidate.cover_url) editCoverUrl = candidate.cover_url;

		metadataValues = newValues;
	}

	async function handleSearchIsbn(isbn: string): Promise<EnrichedResult> {
		if (!currentFile) throw new Error('No file selected');
		return await enrichByIsbn(currentFile.id, isbn);
	}

	async function handleSearchTitle(title: string, author?: string): Promise<SearchCandidate[]> {
		if (!currentFile) throw new Error('No file selected');
		const result = await searchByTitle(currentFile.id, title, author);
		return result.candidates;
	}

	function handleCoverClick(url: string, title: string) {
		lightboxImage = url;
		lightboxTitle = title;
	}

	function clearMessages() {
		error = null;
		success = null;
	}

	async function handleSkip() {
		// Clear search state for next file
		searchPanel?.reset();
		// Navigate to next file
		const nextSkip = data.currentSkip + 1;
		await goto(`/review?skip=${nextSkip}${data.currentFormat ? `&format=${data.currentFormat}` : ''}`);
	}

	async function handleFile() {
		if (!currentFile) return;

		// Validate we have at least a title
		if (!metadataValues.title.trim()) {
			error = 'Title is required to file';
			return;
		}

		clearMessages();
		isLoading = true;

		try {
			// Build options with edited metadata
			const options: FileSourceOptions = {
				edited_title: metadataValues.title.trim(),
				edited_authors: metadataValues.authors.filter((a) => a.trim()),
				edited_isbn: metadataValues.isbn.trim() || undefined,
				edited_publisher: metadataValues.publisher.trim() || undefined,
				edited_publish_date: metadataValues.publishDate.trim() || undefined,
				edited_series: metadataValues.series.trim() || undefined,
				edited_series_index: metadataValues.seriesIndex ? parseFloat(metadataValues.seriesIndex) : undefined,
				edited_description: metadataValues.description.trim() || undefined,
				force_ddc: metadataValues.ddc.trim() || undefined
			};

			const result = await fileSourceFile(currentFile.id, options);

			if (result.success) {
				if (result.was_duplicate) {
					success = `Marked as duplicate of: "${result.duplicate_of_title}"`;
				} else {
					success = `Filed as: ${result.item_title}`;
				}
				// Clear search state for next file
				searchPanel?.reset();
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
			searchPanel?.reset();
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
						<MetadataForm
							values={metadataValues}
							onChange={handleMetadataChange}
							variant="blue"
						/>
					</div>
				</div>

				<!-- Search panels -->
				<SearchPanel
					bind:this={searchPanel}
					initialIsbn={initialSearchIsbn}
					initialTitle={initialSearchTitle}
					initialAuthor={initialSearchAuthor}
					onSearchIsbn={handleSearchIsbn}
					onSearchTitle={handleSearchTitle}
					onSelectCandidate={handleSelectCandidate}
					onMergeResult={handleMergeResult}
					onReplaceResult={handleReplaceResult}
					onCoverClick={handleCoverClick}
				/>

				<!-- Actions -->
				<div class="flex flex-wrap gap-3 mt-6">
					<button
						onclick={handleFile}
						disabled={isLoading || !metadataValues.title.trim()}
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
<Lightbox
	imageUrl={lightboxImage}
	title={lightboxTitle}
	onClose={() => (lightboxImage = null)}
/>
