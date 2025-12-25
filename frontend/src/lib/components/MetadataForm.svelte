<script lang="ts">
	import { getAuthors, getSeries, type AuthorSummary, type SeriesSummary } from '$lib/api';

	/**
	 * Metadata values for the form
	 */
	export interface MetadataValues {
		title: string;
		authors: string[];
		isbn: string;
		ddc: string;
		series: string;
		seriesIndex: string;
		publisher: string;
		publishDate: string;
		description: string;
	}

	interface Props {
		values: MetadataValues;
		onChange: (values: MetadataValues) => void;
		/** Whether to show publisher/date fields */
		showPublisher?: boolean;
		/** Whether to show description field */
		showDescription?: boolean;
		/** Label style - 'blue' for review page highlight, 'default' for normal */
		variant?: 'default' | 'blue';
	}

	let {
		values,
		onChange,
		showPublisher = true,
		showDescription = true,
		variant = 'default'
	}: Props = $props();

	// Author autocomplete state
	let authorQuery = $state('');
	let authorSuggestions = $state<AuthorSummary[]>([]);
	let showAuthorSuggestions = $state(false);

	// Series autocomplete state
	let seriesSuggestions = $state<SeriesSummary[]>([]);
	let showSeriesSuggestions = $state(false);

	// Derived styles based on variant
	const labelClass = $derived(
		variant === 'blue'
			? 'text-blue-600 dark:text-blue-400'
			: 'text-gray-700 dark:text-gray-300'
	);
	const inputBorderClass = $derived(
		variant === 'blue'
			? 'border-blue-200 dark:border-blue-700'
			: 'border-gray-300 dark:border-gray-600'
	);

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
		if (name && !values.authors.includes(name)) {
			onChange({ ...values, authors: [...values.authors, name] });
		}
		authorQuery = '';
		showAuthorSuggestions = false;
	}

	function removeAuthor(index: number) {
		onChange({ ...values, authors: values.authors.filter((_, i) => i !== index) });
	}

	function selectSeries(name: string) {
		onChange({ ...values, series: name });
		showSeriesSuggestions = false;
	}

	function updateField<K extends keyof MetadataValues>(field: K, value: MetadataValues[K]) {
		onChange({ ...values, [field]: value });
	}
</script>

<div class="space-y-3">
	<!-- Title -->
	<div>
		<label for="meta-title" class="block text-xs font-medium {labelClass} mb-1">
			Title
		</label>
		<input
			id="meta-title"
			type="text"
			value={values.title}
			oninput={(e) => updateField('title', e.currentTarget.value)}
			class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
			placeholder="Enter title..."
		/>
	</div>

	<!-- Authors with autocomplete -->
	<div>
		<span class="block text-xs font-medium {labelClass} mb-1">
			Authors
		</span>
		<!-- Current authors -->
		<div class="flex flex-wrap gap-1 mb-2">
			{#each values.authors as author, i}
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
				class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
			<label for="meta-isbn" class="block text-xs font-medium {labelClass} mb-1">
				ISBN
			</label>
			<input
				id="meta-isbn"
				type="text"
				value={values.isbn}
				oninput={(e) => updateField('isbn', e.currentTarget.value)}
				class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				placeholder="ISBN..."
			/>
		</div>
		<div>
			<label for="meta-ddc" class="block text-xs font-medium {labelClass} mb-1">
				DDC Classification
			</label>
			<input
				id="meta-ddc"
				type="text"
				value={values.ddc}
				oninput={(e) => updateField('ddc', e.currentTarget.value)}
				class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				placeholder="e.g. 813.54"
			/>
		</div>
	</div>

	<!-- Series with autocomplete -->
	<div class="grid grid-cols-3 gap-3">
		<div class="col-span-2 relative">
			<label for="meta-series" class="block text-xs font-medium {labelClass} mb-1">
				Series
			</label>
			<input
				id="meta-series"
				type="text"
				value={values.series}
				oninput={(e) => {
					updateField('series', e.currentTarget.value);
					searchSeriesNames(e.currentTarget.value);
					showSeriesSuggestions = true;
				}}
				onfocus={() => {
					if (values.series.length >= 2) {
						searchSeriesNames(values.series);
						showSeriesSuggestions = true;
					}
				}}
				onblur={() => setTimeout(() => (showSeriesSuggestions = false), 200)}
				class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
			<label for="meta-series-index" class="block text-xs font-medium {labelClass} mb-1">
				# in Series
			</label>
			<input
				id="meta-series-index"
				type="text"
				value={values.seriesIndex}
				oninput={(e) => updateField('seriesIndex', e.currentTarget.value)}
				class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				placeholder="1"
			/>
		</div>
	</div>

	<!-- Publisher and date -->
	{#if showPublisher}
		<div class="grid grid-cols-2 gap-3">
			<div>
				<label for="meta-publisher" class="block text-xs font-medium {labelClass} mb-1">
					Publisher
				</label>
				<input
					id="meta-publisher"
					type="text"
					value={values.publisher}
					oninput={(e) => updateField('publisher', e.currentTarget.value)}
					class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					placeholder="Publisher..."
				/>
			</div>
			<div>
				<label for="meta-publish-date" class="block text-xs font-medium {labelClass} mb-1">
					Publish Date
				</label>
				<input
					id="meta-publish-date"
					type="text"
					value={values.publishDate}
					oninput={(e) => updateField('publishDate', e.currentTarget.value)}
					class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					placeholder="Year or date..."
				/>
			</div>
		</div>
	{/if}

	<!-- Description -->
	{#if showDescription}
		<div>
			<label for="meta-description" class="block text-xs font-medium {labelClass} mb-1">
				Description
			</label>
			<textarea
				id="meta-description"
				value={values.description}
				oninput={(e) => updateField('description', e.currentTarget.value)}
				rows="3"
				class="w-full px-3 py-1.5 text-sm border {inputBorderClass} rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
				placeholder="Book description..."
			></textarea>
		</div>
	{/if}
</div>
