<script lang="ts">
	import type { SearchCandidate, ItemSearchCandidate } from '$lib/api';

	// Accept both review queue candidates and item enrichment candidates
	type CandidateType = SearchCandidate | ItemSearchCandidate;

	interface Props {
		candidate: CandidateType;
		onSelect: (candidate: CandidateType) => void;
		onCoverClick?: (url: string, title: string) => void;
		onUseCover?: (url: string) => void;
	}

	let { candidate, onSelect, onCoverClick, onUseCover }: Props = $props();
</script>

<div class="bg-white dark:bg-gray-800 border border-blue-100 dark:border-blue-700 rounded-lg p-3 hover:border-blue-300 dark:hover:border-blue-500 transition-colors">
	<div class="flex gap-3">
		<!-- Cover thumbnail -->
		{#if candidate.cover_url}
			<button
				type="button"
				onclick={() => onCoverClick?.(candidate.cover_url!, candidate.title || 'Cover')}
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

		<!-- Action buttons -->
		<div class="flex flex-col gap-1.5 flex-shrink-0 self-center">
			<button
				onclick={() => onSelect(candidate)}
				class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 font-medium"
			>
				Use
			</button>
			{#if candidate.cover_url && onUseCover}
				<button
					onclick={() => onUseCover?.(candidate.cover_url!)}
					class="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm rounded hover:bg-gray-300 dark:hover:bg-gray-600 font-medium"
					title="Use only the cover image"
				>
					Cover
				</button>
			{/if}
		</div>
	</div>
</div>
