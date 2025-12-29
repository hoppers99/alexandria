<script lang="ts">
	import { onMount } from 'svelte';
	import {
		formatBytes,
		updateItem,
		requestRefile,
		requestAuthorFix,
		removeCreator,
		getPiles,
		getPilesForItem,
		addItemsToPile,
		removeItemsFromPile,
		enrichItemByIsbn,
		searchItemByTitle,
		setItemCover,
		uploadItemCover,
		setItemBackdrop,
		uploadItemBackdrop,
		removeItemBackdrop,
		getReadingProgress,
		markAsFinished,
		markAsUnfinished,
		type ItemDetail,
		type ItemUpdate,
		type PileSummary,
		type ItemEnrichedResult,
		type ItemSearchCandidate,
		type ReadingProgress
	} from '$lib/api';
	import { getLanguageName, formatDdcDisplay } from '$lib/format';
	import { Lightbox, SearchCandidateCard, SearchResultCard } from '$lib/components';

	interface Props {
		data: {
			item: ItemDetail;
		};
	}

	let { data }: Props = $props();
	let item = $state(data.item);

	// Piles state
	let showPileModal = $state(false);
	let allPiles = $state<PileSummary[]>([]);
	let itemPiles = $state<PileSummary[]>([]);
	let loadingPiles = $state(false);
	let addingToPile = $state(false);

	// Reading progress state
	let readingProgress = $state<ReadingProgress | null>(null);
	let markingProgress = $state(false);

	// Load piles and reading progress on mount
	onMount(async () => {
		try {
			const [pilesResult, progressResult] = await Promise.all([
				getPilesForItem(item.id),
				getReadingProgress(item.id).catch(() => ({ success: false, progress: null }))
			]);
			itemPiles = pilesResult;
			readingProgress = progressResult.progress;
		} catch (err) {
			console.error('Failed to load item data:', err);
		}
	});

	async function openPileModal() {
		showPileModal = true;
		loadingPiles = true;
		try {
			const [allResult, itemResult] = await Promise.all([
				getPiles(),
				getPilesForItem(item.id)
			]);
			allPiles = allResult.piles;
			itemPiles = itemResult;
		} catch (err) {
			console.error('Failed to load piles:', err);
		} finally {
			loadingPiles = false;
		}
	}

	// Check if item is in a specific pile
	function isInPile(pileId: number): boolean {
		return itemPiles.some(p => p.id === pileId);
	}

	async function addToPile(pileId: number) {
		addingToPile = true;
		try {
			await addItemsToPile(pileId, [item.id]);
			// Refresh item piles
			itemPiles = await getPilesForItem(item.id);
		} catch (err) {
			console.error('Failed to add to pile:', err);
		} finally {
			addingToPile = false;
		}
	}

	async function removeFromPile(pileId: number) {
		addingToPile = true;
		try {
			await removeItemsFromPile(pileId, [item.id]);
			// Refresh item piles
			itemPiles = await getPilesForItem(item.id);
		} catch (err) {
			console.error('Failed to remove from pile:', err);
		} finally {
			addingToPile = false;
		}
	}

	async function handleMarkAsFinished() {
		markingProgress = true;
		try {
			const result = await markAsFinished(item.id);
			readingProgress = result.progress;
			// Refresh piles (item may have moved to "Read" pile)
			itemPiles = await getPilesForItem(item.id);
		} catch (err) {
			console.error('Failed to mark as finished:', err);
		} finally {
			markingProgress = false;
		}
	}

	async function handleMarkAsUnfinished() {
		markingProgress = true;
		try {
			const result = await markAsUnfinished(item.id);
			readingProgress = result.progress;
			// Refresh piles (item may have moved to "Currently Reading" pile)
			itemPiles = await getPilesForItem(item.id);
		} catch (err) {
			console.error('Failed to mark as unfinished:', err);
		} finally {
			markingProgress = false;
		}
	}

	const authors = $derived(item.creators.filter((c) => c.role === 'author').map((c) => c.name));

	const otherCreators = $derived(item.creators.filter((c) => c.role !== 'author'));

	// Edit modal state
	let showEditModal = $state(false);
	let editTab = $state<'metadata' | 'enrich' | 'cover' | 'backdrop' | 'refile' | 'authors'>('metadata');
	let saving = $state(false);
	let saveError = $state<string | null>(null);
	let saveSuccess = $state<string | null>(null);

	// Lightbox state
	let lightboxImage = $state<string | null>(null);
	let lightboxTitle = $state('');

	// Enrich tab state
	let showIsbnSearch = $state(false);
	let showTitleSearch = $state(false);
	let searchIsbn = $state('');
	let searchTitle = $state('');
	let searchAuthor = $state('');
	let isSearching = $state(false);
	let searchResult = $state<ItemEnrichedResult | null>(null);
	let searchCandidates = $state<ItemSearchCandidate[]>([]);

	// Form state
	let editTitle = $state(item.title);
	let editSubtitle = $state(item.subtitle || '');
	let editDescription = $state(item.description || '');
	let editSeriesName = $state(item.series_name || '');
	let editSeriesIndex = $state(item.series_index?.toString() || '');
	let editTags = $state(item.tags?.join(', ') || '');

	// Refile state
	let refileCategory = $state<'fiction' | 'non-fiction' | ''>('');
	let refileDdc = $state('');

	// Author fix state
	let selectedCreatorId = $state<number | null>(null);
	let correctedAuthorName = $state('');

	// Cover upload state
	let coverFileInput = $state<HTMLInputElement | null>(null);
	let coverUrlInput = $state('');

	// Backdrop upload state
	let backdropFileInput = $state<HTMLInputElement | null>(null);
	let backdropUrlInput = $state('');

	async function handleBackdropUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (!input.files?.length) return;

		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			const result = await uploadItemBackdrop(item.id, input.files[0]);
			if (result.success && result.backdrop_url) {
				item = { ...item, backdrop_url: `${result.backdrop_url}?t=${Date.now()}` };
				saveSuccess = 'Backdrop uploaded successfully';
			}
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to upload backdrop';
		} finally {
			saving = false;
			if (input) input.value = '';
		}
	}

	async function handleBackdropFromUrl() {
		if (!backdropUrlInput.trim()) return;

		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			const result = await setItemBackdrop(item.id, backdropUrlInput.trim());
			if (result.success && result.backdrop_url) {
				item = { ...item, backdrop_url: `${result.backdrop_url}?t=${Date.now()}` };
				saveSuccess = 'Backdrop set successfully';
			}
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to set backdrop';
		} finally {
			saving = false;
			backdropUrlInput = '';
		}
	}

	async function handleRemoveBackdrop() {
		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			await removeItemBackdrop(item.id);
			item = { ...item, backdrop_url: null };
			saveSuccess = 'Backdrop removed';
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to remove backdrop';
		} finally {
			saving = false;
		}
	}

	async function handleCoverUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (!input.files?.length) return;

		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			const result = await uploadItemCover(item.id, input.files[0]);
			if (result.success && result.cover_url) {
				item = { ...item, cover_url: `${result.cover_url}?t=${Date.now()}` };
				saveSuccess = 'Cover uploaded successfully';
			}
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to upload cover';
		} finally {
			saving = false;
			if (input) input.value = '';
		}
	}

	async function handleCoverFromUrl() {
		if (!coverUrlInput.trim()) return;
		await handleUseCover(coverUrlInput.trim());
		coverUrlInput = '';
	}

	function openEditModal() {
		// Reset form to current values
		editTitle = item.title;
		editSubtitle = item.subtitle || '';
		editDescription = item.description || '';
		editSeriesName = item.series_name || '';
		editSeriesIndex = item.series_index?.toString() || '';
		editTags = item.tags?.join(', ') || '';
		refileCategory = '';
		refileDdc = '';
		selectedCreatorId = null;
		correctedAuthorName = '';
		// Reset enrich state
		searchIsbn = item.isbn13 || item.isbn || '';
		searchTitle = item.title;
		searchAuthor = authors[0] || '';
		searchResult = null;
		searchCandidates = [];
		showIsbnSearch = false;
		showTitleSearch = false;
		saveError = null;
		saveSuccess = null;
		showEditModal = true;
	}

	// Enrich search functions
	async function handleSearchIsbn() {
		if (!searchIsbn.trim()) return;

		isSearching = true;
		saveError = null;
		searchResult = null;

		try {
			const result = await enrichItemByIsbn(item.id, searchIsbn.trim());
			searchResult = result;

			if (!result.found) {
				saveError = 'No results found for that ISBN';
			}
		} catch (err) {
			saveError = err instanceof Error ? err.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	async function handleSearchTitle() {
		if (!searchTitle.trim()) return;

		isSearching = true;
		saveError = null;
		searchResult = null;
		searchCandidates = [];

		try {
			const result = await searchItemByTitle(
				item.id,
				searchTitle.trim(),
				searchAuthor.trim() || undefined
			);
			searchCandidates = result.candidates;

			if (result.candidates.length === 0) {
				saveError = 'No results found';
			}
		} catch (err) {
			saveError = err instanceof Error ? err.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	function applyCandidate(candidate: ItemSearchCandidate) {
		// Apply candidate data to edit fields
		if (candidate.title) editTitle = candidate.title;
		if (candidate.description) editDescription = candidate.description;
		if (candidate.series) {
			editSeriesName = candidate.series;
			if (candidate.series_number) editSeriesIndex = candidate.series_number.toString();
		}

		// Clear candidates after selection
		searchCandidates = [];
		saveSuccess = 'Metadata applied to form. Switch to Metadata tab to review and save.';
	}

	function applySearchResultMerge() {
		if (!searchResult || !searchResult.found) return;

		// Only fill in empty fields
		if (!editTitle && searchResult.title) editTitle = searchResult.title;
		if (!editDescription && searchResult.description) editDescription = searchResult.description;
		if (!editSeriesName && searchResult.series) {
			editSeriesName = searchResult.series;
			if (searchResult.series_number) editSeriesIndex = searchResult.series_number.toString();
		}

		searchResult = null;
		saveSuccess = 'Metadata merged. Switch to Metadata tab to review and save.';
	}

	function applySearchResultReplace() {
		if (!searchResult || !searchResult.found) return;

		if (searchResult.title) editTitle = searchResult.title;
		if (searchResult.description) editDescription = searchResult.description;
		if (searchResult.series) {
			editSeriesName = searchResult.series;
			if (searchResult.series_number) editSeriesIndex = searchResult.series_number.toString();
		}

		searchResult = null;
		saveSuccess = 'Metadata replaced. Switch to Metadata tab to review and save.';
	}

	function openLightbox(url: string, title: string) {
		lightboxImage = url;
		lightboxTitle = title;
	}

	async function handleUseCover(url: string) {
		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			const result = await setItemCover(item.id, url);
			if (result.success && result.cover_url) {
				// Update local state with cache-busting query param
				item = { ...item, cover_url: `${result.cover_url}?t=${Date.now()}` };
				saveSuccess = 'Cover updated successfully';
			}
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to set cover';
		} finally {
			saving = false;
		}
	}

	function closeEditModal() {
		showEditModal = false;
	}

	async function saveMetadata() {
		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			const updates: ItemUpdate = {};

			if (editTitle !== item.title) updates.title = editTitle;
			if (editSubtitle !== (item.subtitle || '')) updates.subtitle = editSubtitle || undefined;
			if (editDescription !== (item.description || ''))
				updates.description = editDescription || undefined;
			if (editSeriesName !== (item.series_name || ''))
				updates.series_name = editSeriesName || undefined;
			if (editSeriesIndex !== (item.series_index?.toString() || '')) {
				updates.series_index = editSeriesIndex ? parseFloat(editSeriesIndex) : undefined;
			}

			const newTags = editTags
				.split(',')
				.map((t) => t.trim())
				.filter((t) => t);
			const oldTags = item.tags || [];
			if (JSON.stringify(newTags) !== JSON.stringify(oldTags)) {
				updates.tags = newTags;
			}

			if (Object.keys(updates).length === 0) {
				saveSuccess = 'No changes to save';
				return;
			}

			const updatedItem = await updateItem(item.id, updates);
			item = updatedItem;
			saveSuccess = 'Changes saved successfully';
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to save changes';
		} finally {
			saving = false;
		}
	}

	async function submitRefile() {
		if (!refileCategory && !refileDdc) {
			saveError = 'Select a category or enter a DDC code';
			return;
		}

		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			await requestRefile(item.id, {
				target_category: refileCategory || undefined,
				target_ddc: refileDdc || undefined
			});
			saveSuccess = 'Refile request submitted. The librarian will process it shortly.';
			refileCategory = '';
			refileDdc = '';
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to submit refile request';
		} finally {
			saving = false;
		}
	}

	async function submitAuthorFix() {
		if (!selectedCreatorId || !correctedAuthorName.trim()) {
			saveError = 'Select an author and enter the corrected name';
			return;
		}

		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			await requestAuthorFix(item.id, {
				creator_id: selectedCreatorId,
				corrected_name: correctedAuthorName.trim()
			});
			saveSuccess = 'Author fix request submitted. The librarian will process it shortly.';
			selectedCreatorId = null;
			correctedAuthorName = '';
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to submit author fix request';
		} finally {
			saving = false;
		}
	}

	function selectCreatorForFix(creatorId: number, currentName: string) {
		selectedCreatorId = creatorId;
		// Try to auto-fix common patterns
		if (currentName.includes('|')) {
			// "Lastname|Firstname" -> "Firstname Lastname"
			const parts = currentName.split('|');
			correctedAuthorName = parts.reverse().join(' ');
		} else if (currentName.includes(';')) {
			// Multiple authors - just take the first and clean it
			correctedAuthorName = currentName.split(';')[0].trim();
		} else {
			correctedAuthorName = currentName;
		}
	}

	async function handleRemoveCreator(creatorId: number, creatorName: string) {
		if (!confirm(`Remove "${creatorName}" from this book?`)) {
			return;
		}

		saving = true;
		saveError = null;
		saveSuccess = null;

		try {
			const updatedItem = await removeCreator(item.id, creatorId);
			item = updatedItem;
			saveSuccess = `Removed "${creatorName}" from this book`;
			selectedCreatorId = null;
			correctedAuthorName = '';
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to remove creator';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head>
	<title>{item.title} - Alexandria</title>
</svelte:head>

<!-- Hero backdrop section -->
<div class="relative">
	<!-- Backdrop image (blurred cover as fallback, or custom backdrop) -->
	{#if item.backdrop_url || item.cover_url}
		<div class="absolute inset-x-0 top-0 h-48 md:h-64 lg:h-80 overflow-hidden">
			<img
				src={item.backdrop_url || item.cover_url}
				alt=""
				class="w-full h-full object-cover {item.backdrop_url ? '' : 'blur-sm scale-110'}"
			/>
			<!-- Gradient overlay for readability -->
			<div class="absolute inset-0 bg-gradient-to-b from-black/30 via-black/50 to-gray-50 dark:to-gray-900"></div>
		</div>
	{:else}
		<!-- Fallback gradient when no images available -->
		<div class="absolute inset-x-0 top-0 h-48 md:h-64 lg:h-80 bg-gradient-to-b from-gray-300 to-gray-50 dark:from-gray-700 dark:to-gray-900"></div>
	{/if}

	<!-- Content overlaid on backdrop -->
	<div class="relative z-10">
		<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 md:pt-10">
			<!-- Back button - styled for visibility on backdrop -->
			<a
				href="/browse"
				class="inline-flex items-center text-white/90 hover:text-white mb-6 drop-shadow-md"
			>
				<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				Back to Library
			</a>

			<div class="flex flex-col md:flex-row gap-8">
				<!-- Cover -->
				<div class="flex-shrink-0">
					<div
						class="w-48 md:w-64 aspect-[2/3] bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden shadow-2xl ring-1 ring-white/20"
					>
						{#if item.cover_url}
							<img src={item.cover_url} alt={item.title} class="w-full h-full object-cover" />
						{:else}
							<div class="w-full h-full flex items-center justify-center p-4">
								<span class="text-gray-400 dark:text-gray-500 text-center">
									{item.title}
								</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Details -->
				<div class="flex-1">
					<div class="flex items-start justify-between gap-4">
						<h1 class="text-3xl font-bold text-white drop-shadow-lg mb-2">
							{item.title}
						</h1>
						<button
							onclick={openEditModal}
							class="flex-shrink-0 p-2 text-white/80 hover:text-white rounded-lg hover:bg-white/20"
							aria-label="Edit book"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
								/>
							</svg>
						</button>
					</div>

					{#if item.subtitle}
						<p class="text-xl text-white/80 drop-shadow mb-2">
							{item.subtitle}
						</p>
					{/if}

					{#if authors.length > 0}
						<p class="text-lg text-white/90 drop-shadow mb-4">
							by {authors.join(', ')}
						</p>
					{/if}

					{#if item.series_name}
						<p class="text-blue-300 drop-shadow mb-4">
							<a href="/series/{encodeURIComponent(item.series_name)}" class="hover:underline">
								{item.series_name}
							</a>
							{#if item.series_index}
								<span class="text-white/60">#{item.series_index}</span>
							{/if}
						</p>
					{/if}

			<!-- Action buttons -->
			<div class="flex flex-wrap gap-3 mb-6">
				{#each item.files as file}
					<a
						href="/api/items/{item.id}/files/{file.id}/download"
						class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
					>
						<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
							/>
						</svg>
						{file.format.toUpperCase()}
						{#if file.size_bytes}
							<span class="ml-1 text-blue-200">({formatBytes(file.size_bytes)})</span>
						{/if}
					</a>
				{/each}

				{#if item.files.some((f) => ['epub', 'mobi', 'azw', 'azw3', 'fb2', 'fbz', 'cbz'].includes(f.format))}
					<a
						href="/read/{item.id}"
						class="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
					>
						<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
							/>
						</svg>
						{readingProgress && readingProgress.progress > 0 ? 'Continue Reading' : 'Read'}
					</a>
				{/if}

				<button
					onclick={openPileModal}
					class="inline-flex items-center px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg font-medium transition-colors"
				>
					<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
						/>
					</svg>
					Add to Pile
				</button>
			</div>

			<!-- Reading Progress -->
			{#if readingProgress?.finished_at}
				<!-- Finished state -->
				<div class="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-2">
							<svg class="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
							</svg>
							<span class="text-sm font-medium text-green-800 dark:text-green-200">
								Finished Reading
							</span>
						</div>
						<button
							onclick={handleMarkAsUnfinished}
							disabled={markingProgress}
							class="text-sm px-3 py-1 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-800/50 rounded-lg transition-colors disabled:opacity-50"
						>
							{markingProgress ? 'Updating...' : 'Mark as Unfinished'}
						</button>
					</div>
					<p class="mt-2 text-xs text-green-600 dark:text-green-400">
						Finished on {new Date(readingProgress.finished_at).toLocaleDateString()}
					</p>
				</div>
			{:else if readingProgress && readingProgress.progress > 0}
				<!-- In progress state -->
				<div class="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-blue-800 dark:text-blue-200">
							Reading Progress
						</span>
						<div class="flex items-center gap-3">
							<span class="text-sm text-blue-600 dark:text-blue-300">
								{Math.round(readingProgress.progress * 100)}%
								{#if readingProgress.location_label}
									· {readingProgress.location_label}
								{/if}
							</span>
							<button
								onclick={handleMarkAsFinished}
								disabled={markingProgress}
								class="text-sm px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
							>
								{markingProgress ? 'Updating...' : 'Mark as Finished'}
							</button>
						</div>
					</div>
					<div class="w-full h-2 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden">
						<div
							class="h-full bg-blue-600 dark:bg-blue-400 transition-all duration-300"
							style="width: {Math.round(readingProgress.progress * 100)}%;"
						></div>
					</div>
					{#if readingProgress.last_read_at}
						<p class="mt-2 text-xs text-blue-600 dark:text-blue-400">
							Last read: {new Date(readingProgress.last_read_at).toLocaleDateString()} at {new Date(readingProgress.last_read_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
						</p>
					{/if}
				</div>
			{:else}
				<!-- Not started state - show Mark as Read button -->
				<div class="mb-6">
					<button
						onclick={handleMarkAsFinished}
						disabled={markingProgress}
						class="inline-flex items-center px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg font-medium transition-colors disabled:opacity-50"
					>
						<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
						{markingProgress ? 'Updating...' : 'Mark as Read'}
					</button>
				</div>
			{/if}

			<!-- Description -->
			{#if item.description}
				<div class="mb-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Description</h2>
					<div class="prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-300">
						{@html item.description}
					</div>
				</div>
			{/if}

			<!-- Metadata -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
				{#if item.publisher}
					<div>
						<span class="text-gray-500 dark:text-gray-400">Publisher:</span>
						<span class="ml-2 text-gray-900 dark:text-white">{item.publisher}</span>
					</div>
				{/if}

				{#if item.publish_date}
					<div>
						<span class="text-gray-500 dark:text-gray-400">Published:</span>
						<span class="ml-2 text-gray-900 dark:text-white">
							{new Date(item.publish_date).getFullYear()}
						</span>
					</div>
				{/if}

				{#if item.isbn13 || item.isbn}
					<div>
						<span class="text-gray-500 dark:text-gray-400">ISBN:</span>
						<span class="ml-2 text-gray-900 dark:text-white font-mono">
							{item.isbn13 || item.isbn}
						</span>
					</div>
				{/if}

				{#if item.language}
					<div>
						<span class="text-gray-500 dark:text-gray-400">Language:</span>
						<span class="ml-2 text-gray-900 dark:text-white">{getLanguageName(item.language)}</span>
					</div>
				{/if}

				{#if item.page_count}
					<div>
						<span class="text-gray-500 dark:text-gray-400">Pages:</span>
						<span class="ml-2 text-gray-900 dark:text-white">{item.page_count}</span>
					</div>
				{/if}

				{#if item.classification_code}
					<div>
						<span class="text-gray-500 dark:text-gray-400">Classification:</span>
						<span class="ml-2 text-gray-900 dark:text-white">{formatDdcDisplay(item.classification_code)}</span>
					</div>
				{/if}

				<div>
					<span class="text-gray-500 dark:text-gray-400">Added:</span>
					<span class="ml-2 text-gray-900 dark:text-white">
						{new Date(item.date_added).toLocaleDateString()}
					</span>
				</div>
			</div>

			<!-- Tags -->
			{#if item.tags && item.tags.length > 0}
				<div class="mt-6">
					<h2 class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">Tags</h2>
					<div class="flex flex-wrap gap-2">
						{#each item.tags as tag}
							<a
								href="/browse?tag={encodeURIComponent(tag)}"
								class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm hover:bg-gray-200 dark:hover:bg-gray-600"
							>
								{tag}
							</a>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Other creators -->
			{#if otherCreators.length > 0}
				<div class="mt-6">
					<h2 class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">Contributors</h2>
					<div class="space-y-1">
						{#each otherCreators as creator}
							<div class="text-sm text-gray-700 dark:text-gray-300">
								<span class="capitalize text-gray-500 dark:text-gray-400">{creator.role}:</span>
								{creator.name}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Piles -->
			{#if itemPiles.length > 0}
				<div class="mt-6">
					<h2 class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">In Piles</h2>
					<div class="flex flex-wrap gap-2">
						{#each itemPiles as pile}
							<a
								href="/piles/{pile.id}"
								class="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm hover:bg-green-200 dark:hover:bg-green-900/50"
							>
								{pile.name}
							</a>
						{/each}
					</div>
				</div>
			{/if}
			</div>
		</div>
		</div>
	</div>
</div>

<!-- Edit Modal -->
{#if showEditModal}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		onclick={(e) => e.target === e.currentTarget && closeEditModal()}
		role="dialog"
		aria-modal="true"
	>
		<div
			class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full h-[80vh] overflow-hidden flex flex-col"
		>
			<!-- Modal header -->
			<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Edit Book</h2>
				<button
					onclick={closeEditModal}
					class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<!-- Tabs -->
			<div class="flex border-b border-gray-200 dark:border-gray-700">
				<button
					class="px-4 py-3 text-sm font-medium {editTab === 'metadata'
						? 'text-blue-600 border-b-2 border-blue-600'
						: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
					onclick={() => (editTab = 'metadata')}
				>
					Metadata
				</button>
				<button
					class="px-4 py-3 text-sm font-medium {editTab === 'enrich'
						? 'text-blue-600 border-b-2 border-blue-600'
						: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
					onclick={() => (editTab = 'enrich')}
				>
					Enrich
				</button>
				<button
					class="px-4 py-3 text-sm font-medium {editTab === 'cover'
						? 'text-blue-600 border-b-2 border-blue-600'
						: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
					onclick={() => (editTab = 'cover')}
				>
					Cover
				</button>
				<button
					class="px-4 py-3 text-sm font-medium {editTab === 'backdrop'
						? 'text-blue-600 border-b-2 border-blue-600'
						: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
					onclick={() => (editTab = 'backdrop')}
				>
					Backdrop
				</button>
				<button
					class="px-4 py-3 text-sm font-medium {editTab === 'refile'
						? 'text-blue-600 border-b-2 border-blue-600'
						: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
					onclick={() => (editTab = 'refile')}
				>
					Refile
				</button>
				<button
					class="px-4 py-3 text-sm font-medium {editTab === 'authors'
						? 'text-blue-600 border-b-2 border-blue-600'
						: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
					onclick={() => (editTab = 'authors')}
				>
					Authors
				</button>
			</div>

			<!-- Modal body -->
			<div class="flex-1 overflow-y-auto p-4">
				{#if saveError}
					<div class="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg">
						{saveError}
					</div>
				{/if}
				{#if saveSuccess}
					<div class="mb-4 p-3 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg">
						{saveSuccess}
					</div>
				{/if}

				{#if editTab === 'metadata'}
					<div class="space-y-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Title
							</label>
							<input
								type="text"
								bind:value={editTitle}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Subtitle
							</label>
							<input
								type="text"
								bind:value={editSubtitle}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							/>
						</div>

						<div class="grid grid-cols-2 gap-4">
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									Series Name
								</label>
								<input
									type="text"
									bind:value={editSeriesName}
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									Series #
								</label>
								<input
									type="text"
									bind:value={editSeriesIndex}
									placeholder="e.g., 1, 2.5"
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								/>
							</div>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Tags (comma-separated)
							</label>
							<input
								type="text"
								bind:value={editTags}
								placeholder="Fiction, Mystery, Thriller"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Description
							</label>
							<textarea
								bind:value={editDescription}
								rows="5"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							></textarea>
						</div>

						<button
							onclick={saveMetadata}
							disabled={saving}
							class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium"
						>
							{saving ? 'Saving...' : 'Save Changes'}
						</button>
					</div>
				{:else if editTab === 'enrich'}
					<div class="space-y-4">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							Search for better metadata from Google Books and Open Library. Select a result to
							apply its metadata to this book.
						</p>

						<!-- Search toggle buttons -->
						<div class="flex gap-2">
							<button
								onclick={() => {
									showIsbnSearch = !showIsbnSearch;
									showTitleSearch = false;
								}}
								class="px-3 py-2 text-sm rounded-lg {showIsbnSearch
									? 'bg-blue-600 text-white'
									: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}"
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
									: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}"
							>
								Search by Title
							</button>
						</div>

						<!-- ISBN search panel -->
						{#if showIsbnSearch}
							<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
								<div class="flex gap-2">
									<input
										type="text"
										bind:value={searchIsbn}
										placeholder="Enter ISBN..."
										class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
										onkeydown={(e) => e.key === 'Enter' && handleSearchIsbn()}
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

						<!-- Title search panel -->
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
										onkeydown={(e) => e.key === 'Enter' && handleSearchTitle()}
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

						<!-- Multiple search candidates (from title search) -->
						{#if searchCandidates.length > 0}
							<div class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
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

								<div class="space-y-3 max-h-64 overflow-y-auto">
									{#each searchCandidates as candidate}
										<SearchCandidateCard
											{candidate}
											onSelect={applyCandidate}
											onCoverClick={openLightbox}
											onUseCover={handleUseCover}
										/>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Single search result (from ISBN search) -->
						{#if searchResult && searchResult.found}
							<SearchResultCard
								result={searchResult}
								onMerge={applySearchResultMerge}
								onReplace={applySearchResultReplace}
								onDismiss={() => (searchResult = null)}
								onCoverClick={openLightbox}
								onUseCover={handleUseCover}
							/>
						{/if}
					</div>
				{:else if editTab === 'cover'}
					<div class="space-y-6">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							Change the cover image by uploading a file or entering an image URL.
						</p>

						<!-- Current cover preview -->
						<div class="flex items-start gap-4">
							<div class="w-32 aspect-[2/3] bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden shadow">
								{#if item.cover_url}
									<img src={item.cover_url} alt={item.title} class="w-full h-full object-cover" />
								{:else}
									<div class="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
										No cover
									</div>
								{/if}
							</div>
							<div class="flex-1 space-y-4">
								<!-- Upload file -->
								<div>
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Upload Image
									</label>
									<input
										type="file"
										accept="image/*"
										bind:this={coverFileInput}
										onchange={handleCoverUpload}
										disabled={saving}
										class="block w-full text-sm text-gray-500 dark:text-gray-400
											file:mr-4 file:py-2 file:px-4
											file:rounded-lg file:border-0
											file:text-sm file:font-medium
											file:bg-blue-50 file:text-blue-700
											dark:file:bg-blue-900/30 dark:file:text-blue-300
											hover:file:bg-blue-100 dark:hover:file:bg-blue-900/50
											file:cursor-pointer cursor-pointer
											disabled:opacity-50 disabled:cursor-not-allowed"
									/>
								</div>

								<!-- Or from URL -->
								<div>
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Or from URL
									</label>
									<div class="flex gap-2">
										<input
											type="url"
											bind:value={coverUrlInput}
											placeholder="https://example.com/cover.jpg"
											disabled={saving}
											class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
											onkeydown={(e) => e.key === 'Enter' && handleCoverFromUrl()}
										/>
										<button
											onclick={handleCoverFromUrl}
											disabled={saving || !coverUrlInput.trim()}
											class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium"
										>
											{saving ? 'Setting...' : 'Set'}
										</button>
									</div>
								</div>
							</div>
						</div>

						<p class="text-xs text-gray-500 dark:text-gray-400">
							Tip: You can also set a cover from search results in the Enrich tab.
						</p>
					</div>
				{:else if editTab === 'backdrop'}
					<div class="space-y-6">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							Set a custom backdrop image for the hero section. If no backdrop is set, the cover image will be used with a blur effect.
						</p>

						<!-- Current backdrop preview -->
						<div class="space-y-4">
							<div class="w-full h-32 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden shadow relative">
								{#if item.backdrop_url}
									<img src={item.backdrop_url} alt="Current backdrop" class="w-full h-full object-cover" />
									<div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
								{:else if item.cover_url}
									<img src={item.cover_url} alt="Cover as backdrop" class="w-full h-full object-cover blur-sm scale-110" />
									<div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
									<span class="absolute bottom-2 left-2 text-xs text-white/80">Using blurred cover</span>
								{:else}
									<div class="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
										No backdrop or cover
									</div>
								{/if}
							</div>

							{#if item.backdrop_url}
								<button
									onclick={handleRemoveBackdrop}
									disabled={saving}
									class="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
								>
									Remove custom backdrop (use blurred cover instead)
								</button>
							{/if}
						</div>

						<div class="flex-1 space-y-4">
							<!-- Upload file -->
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Upload Image
								</label>
								<input
									type="file"
									accept="image/*"
									bind:this={backdropFileInput}
									onchange={handleBackdropUpload}
									disabled={saving}
									class="block w-full text-sm text-gray-500 dark:text-gray-400
										file:mr-4 file:py-2 file:px-4
										file:rounded-lg file:border-0
										file:text-sm file:font-medium
										file:bg-blue-50 file:text-blue-700
										dark:file:bg-blue-900/30 dark:file:text-blue-300
										hover:file:bg-blue-100 dark:hover:file:bg-blue-900/50
										file:cursor-pointer cursor-pointer
										disabled:opacity-50 disabled:cursor-not-allowed"
								/>
							</div>

							<!-- Or from URL -->
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Or from URL
								</label>
								<div class="flex gap-2">
									<input
										type="url"
										bind:value={backdropUrlInput}
										placeholder="https://example.com/backdrop.jpg"
										disabled={saving}
										class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
										onkeydown={(e) => e.key === 'Enter' && handleBackdropFromUrl()}
									/>
									<button
										onclick={handleBackdropFromUrl}
										disabled={saving || !backdropUrlInput.trim()}
										class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium"
									>
										{saving ? 'Setting...' : 'Set'}
									</button>
								</div>
							</div>
						</div>

						<p class="text-xs text-gray-500 dark:text-gray-400">
							Tip: For fiction books, try searching for thematic images (castles for fantasy, spaceships for sci-fi, etc.) on sites like Unsplash or Pexels.
						</p>
					</div>
				{:else if editTab === 'refile'}
					<div class="space-y-4">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							Request to move this book to a different section. The librarian will process this
							request and move the files.
						</p>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Move to Category
							</label>
							<div class="flex gap-4">
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={refileCategory}
										value="fiction"
										class="mr-2"
									/>
									Fiction
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={refileCategory}
										value="non-fiction"
										class="mr-2"
									/>
									Non-Fiction
								</label>
							</div>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Or specify DDC code (for non-fiction)
							</label>
							<input
								type="text"
								bind:value={refileDdc}
								placeholder="e.g., 004, 823.914"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							/>
							<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
								Current: {item.classification_code || 'Not classified'}
							</p>
						</div>

						<button
							onclick={submitRefile}
							disabled={saving || (!refileCategory && !refileDdc)}
							class="w-full px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white rounded-lg font-medium"
						>
							{saving ? 'Submitting...' : 'Submit Refile Request'}
						</button>
					</div>
				{:else if editTab === 'authors'}
					<div class="space-y-4">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							Manage authors and other creators. You can remove incorrect entries or fix badly formatted names.
						</p>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Creators
							</label>
							<div class="space-y-2">
								{#each item.creators as creator}
									<div
										class="flex items-center gap-2 px-3 py-2 border rounded-lg {selectedCreatorId ===
										creator.id
											? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
											: 'border-gray-300 dark:border-gray-600'}"
									>
										<button
											onclick={() => selectCreatorForFix(creator.id, creator.name)}
											class="flex-1 text-left hover:text-blue-600 dark:hover:text-blue-400"
										>
											<span class="text-gray-900 dark:text-white">{creator.name}</span>
											<span class="text-sm text-gray-500 dark:text-gray-400 ml-2">
												({creator.role})
											</span>
										</button>
										<button
											onclick={() => handleRemoveCreator(creator.id, creator.name)}
											disabled={saving}
											class="p-1 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/30 rounded disabled:opacity-50"
											title="Remove from book"
										>
											<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
												/>
											</svg>
										</button>
									</div>
								{/each}
							</div>
						</div>

						{#if selectedCreatorId}
							<div class="pt-4 border-t border-gray-200 dark:border-gray-700">
								<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Fix Name
								</h4>
								<div class="space-y-3">
									<div>
										<label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">
											Corrected Name
										</label>
										<input
											type="text"
											bind:value={correctedAuthorName}
											placeholder="e.g., Terry Goodkind"
											class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
										/>
									</div>

									<button
										onclick={submitAuthorFix}
										disabled={saving || !correctedAuthorName.trim()}
										class="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium"
									>
										{saving ? 'Submitting...' : 'Submit Name Fix'}
									</button>
								</div>
							</div>
						{/if}

						{#if item.creators.length === 0}
							<p class="text-center text-gray-500 dark:text-gray-400 py-4">
								No creators linked to this item.
							</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Manage Piles Modal -->
{#if showPileModal}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		onclick={(e) => e.target === e.currentTarget && (showPileModal = false)}
		role="dialog"
		aria-modal="true"
	>
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Manage Piles</h2>
				<button
					onclick={() => (showPileModal = false)}
					class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			{#if loadingPiles}
				<div class="py-8 text-center text-gray-500 dark:text-gray-400">Loading piles...</div>
			{:else if allPiles.length === 0}
				<div class="py-8 text-center">
					<p class="text-gray-500 dark:text-gray-400 mb-4">You don't have any piles yet.</p>
					<a
						href="/piles"
						class="text-blue-600 dark:text-blue-400 hover:underline"
					>
						Create your first pile
					</a>
				</div>
			{:else}
				<div class="space-y-2 max-h-64 overflow-y-auto">
					{#each allPiles as pile (pile.id)}
						{@const inPile = isInPile(pile.id)}
						<button
							onclick={() => inPile ? removeFromPile(pile.id) : addToPile(pile.id)}
							disabled={addingToPile}
							class="w-full text-left px-4 py-3 rounded-lg border transition-colors disabled:opacity-50 {inPile
								? 'border-green-500 bg-green-50 dark:bg-green-900/30 hover:bg-green-100 dark:hover:bg-green-900/50'
								: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}"
						>
							<div class="flex items-center justify-between">
								<div>
									<div class="font-medium text-gray-900 dark:text-white">{pile.name}</div>
									<div class="text-sm text-gray-500 dark:text-gray-400">
										{pile.item_count} {pile.item_count === 1 ? 'book' : 'books'}
									</div>
								</div>
								{#if inPile}
									<svg class="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
									</svg>
								{/if}
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- Lightbox for cover images -->
<Lightbox
	imageUrl={lightboxImage}
	title={lightboxTitle}
	onClose={() => (lightboxImage = null)}
/>
