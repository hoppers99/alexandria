<script lang="ts">
	import type { EnrichedResult, SearchCandidate } from '$lib/api';
	import SearchCandidateCard from './SearchCandidateCard.svelte';
	import SearchResultCard from './SearchResultCard.svelte';

	interface Props {
		/** Initial ISBN value */
		initialIsbn?: string;
		/** Initial title value */
		initialTitle?: string;
		/** Initial author value */
		initialAuthor?: string;
		/** Callback when ISBN search is requested */
		onSearchIsbn: (isbn: string) => Promise<EnrichedResult>;
		/** Callback when title search is requested */
		onSearchTitle: (title: string, author?: string) => Promise<SearchCandidate[]>;
		/** Callback when a candidate is selected */
		onSelectCandidate: (candidate: SearchCandidate) => void;
		/** Callback to merge enriched result */
		onMergeResult: (result: EnrichedResult) => void;
		/** Callback to replace with enriched result */
		onReplaceResult: (result: EnrichedResult) => void;
		/** Callback when cover is clicked for lightbox */
		onCoverClick?: (url: string, title: string) => void;
	}

	let {
		initialIsbn = '',
		initialTitle = '',
		initialAuthor = '',
		onSearchIsbn,
		onSearchTitle,
		onSelectCandidate,
		onMergeResult,
		onReplaceResult,
		onCoverClick
	}: Props = $props();

	// Search state
	let showIsbnSearch = $state(false);
	let showTitleSearch = $state(false);
	let searchIsbn = $state(initialIsbn);
	let searchTitle = $state(initialTitle);
	let searchAuthor = $state(initialAuthor);
	let isSearching = $state(false);
	let searchError = $state<string | null>(null);

	// Results
	let searchResult = $state<EnrichedResult | null>(null);
	let searchCandidates = $state<SearchCandidate[]>([]);

	// Update initial values when props change
	$effect(() => {
		searchIsbn = initialIsbn;
	});
	$effect(() => {
		searchTitle = initialTitle;
	});
	$effect(() => {
		searchAuthor = initialAuthor;
	});

	async function handleSearchIsbn() {
		if (!searchIsbn.trim()) return;

		isSearching = true;
		searchError = null;
		searchResult = null;

		try {
			const result = await onSearchIsbn(searchIsbn.trim());
			searchResult = result;

			if (!result.found) {
				searchError = 'No results found for that ISBN';
			}
		} catch (err) {
			searchError = err instanceof Error ? err.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	async function handleSearchTitle() {
		if (!searchTitle.trim()) return;

		isSearching = true;
		searchError = null;
		searchResult = null;
		searchCandidates = [];

		try {
			const candidates = await onSearchTitle(searchTitle.trim(), searchAuthor.trim() || undefined);
			searchCandidates = candidates;

			if (candidates.length === 0) {
				searchError = 'No results found';
			}
		} catch (err) {
			searchError = err instanceof Error ? err.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	function handleSelectCandidate(candidate: SearchCandidate) {
		onSelectCandidate(candidate);
		searchCandidates = [];
	}

	function handleMerge() {
		if (searchResult) {
			onMergeResult(searchResult);
			searchResult = null;
		}
	}

	function handleReplace() {
		if (searchResult) {
			onReplaceResult(searchResult);
			searchResult = null;
		}
	}

	function dismissResult() {
		searchResult = null;
	}

	function dismissCandidates() {
		searchCandidates = [];
	}

	/** Reset search state - useful when parent wants to clear after applying */
	export function reset() {
		searchResult = null;
		searchCandidates = [];
		showIsbnSearch = false;
		showTitleSearch = false;
		searchError = null;
	}
</script>

<div class="border-t border-gray-200 dark:border-gray-700 pt-6">
	<!-- Search toggle buttons -->
	<div class="flex gap-2 mb-4">
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

	<!-- Error message -->
	{#if searchError}
		<div class="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
			{searchError}
		</div>
	{/if}

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
		<div class="mt-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
			<div class="flex items-center justify-between mb-3">
				<h4 class="text-sm font-semibold text-blue-800 dark:text-blue-200">
					{searchCandidates.length} Results Found - Select One
				</h4>
				<button
					onclick={dismissCandidates}
					class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
					aria-label="Dismiss"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<div class="space-y-3 max-h-96 overflow-y-auto">
				{#each searchCandidates as candidate}
					<SearchCandidateCard
						{candidate}
						onSelect={handleSelectCandidate}
						{onCoverClick}
					/>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Single search result (from ISBN search) -->
	{#if searchResult}
		<SearchResultCard
			result={searchResult}
			onMerge={handleMerge}
			onReplace={handleReplace}
			onDismiss={dismissResult}
			{onCoverClick}
		/>
	{/if}
</div>
