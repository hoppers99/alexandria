<script lang="ts">
	import type { EnrichedResult, ItemEnrichedResult } from '$lib/api';

	// Accept both review queue results and item enrichment results
	type ResultType = EnrichedResult | ItemEnrichedResult;

	interface Props {
		result: ResultType;
		onMerge: () => void;
		onReplace: () => void;
		onDismiss: () => void;
		onCoverClick?: (url: string, title: string) => void;
		onUseCover?: (url: string) => void;
	}

	let { result, onMerge, onReplace, onDismiss, onCoverClick, onUseCover }: Props = $props();
</script>

{#if result.found}
	<div class="mt-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
		<div class="flex items-start justify-between mb-3">
			<h4 class="text-sm font-semibold text-green-800 dark:text-green-200">
				Match Found - Apply to Metadata?
			</h4>
			<button
				onclick={onDismiss}
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
			{#if result.cover_url}
				<div class="flex-shrink-0">
					<button
						type="button"
						onclick={() => onCoverClick?.(result.cover_url!, 'Search Result Cover')}
						class="cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-green-500 rounded"
					>
						<img
							src={result.cover_url}
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
					<dd class="text-gray-900 dark:text-white">{result.title || '[none]'}</dd>
				</div>
				<div>
					<dt class="text-green-700 dark:text-green-300 font-medium">Authors</dt>
					<dd class="text-gray-900 dark:text-white">{result.authors?.join(', ') || '[none]'}</dd>
				</div>
				{#if result.series}
					<div>
						<dt class="text-green-700 dark:text-green-300 font-medium">Series</dt>
						<dd class="text-gray-900 dark:text-white">
							{result.series}{#if result.series_number} #{result.series_number}{/if}
						</dd>
					</div>
				{/if}
				{#if result.isbn13 || result.isbn}
					<div>
						<dt class="text-green-700 dark:text-green-300 font-medium">ISBN</dt>
						<dd class="text-gray-900 dark:text-white font-mono">{result.isbn13 || result.isbn}</dd>
					</div>
				{/if}
				{#if result.publisher}
					<div>
						<dt class="text-green-700 dark:text-green-300 font-medium">Publisher</dt>
						<dd class="text-gray-900 dark:text-white">{result.publisher}</dd>
					</div>
				{/if}
				{#if result.publish_date}
					<div>
						<dt class="text-green-700 dark:text-green-300 font-medium">Published</dt>
						<dd class="text-gray-900 dark:text-white">{result.publish_date}</dd>
					</div>
				{/if}
				{#if result.ddc}
					<div>
						<dt class="text-green-700 dark:text-green-300 font-medium">DDC Classification</dt>
						<dd class="text-gray-900 dark:text-white font-mono">{result.ddc}</dd>
					</div>
				{/if}
				{#if result.subjects && result.subjects.length > 0}
					<div class="md:col-span-2">
						<dt class="text-green-700 dark:text-green-300 font-medium">Subjects</dt>
						<dd class="text-gray-900 dark:text-white text-xs">{result.subjects.slice(0, 5).join(', ')}</dd>
					</div>
				{/if}
				{#if result.description}
					<div class="md:col-span-2">
						<dt class="text-green-700 dark:text-green-300 font-medium">Description</dt>
						<dd class="text-gray-700 dark:text-gray-300 text-xs line-clamp-3">{result.description}</dd>
					</div>
				{/if}
			</dl>
		</div>

		<!-- Action buttons -->
		<div class="flex flex-wrap gap-2 pt-2 border-t border-green-200 dark:border-green-800">
			<button
				onclick={onMerge}
				class="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 font-medium"
			>
				Merge (fill gaps)
			</button>
			<button
				onclick={onReplace}
				class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 font-medium"
			>
				Replace all
			</button>
			{#if result.cover_url && onUseCover}
				<button
					onclick={() => onUseCover?.(result.cover_url!)}
					class="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 font-medium"
					title="Use only the cover image"
				>
					Use Cover
				</button>
			{/if}
			<button
				onclick={onDismiss}
				class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
			>
				Dismiss
			</button>
		</div>
	</div>
{/if}
