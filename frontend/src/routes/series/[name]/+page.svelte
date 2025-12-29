<script lang="ts">
	import BookCard from '$lib/components/BookCard.svelte';
	import type { SeriesDetail } from '$lib/api';

	interface Props {
		data: {
			series: SeriesDetail;
		};
	}

	let { data }: Props = $props();
</script>

<svelte:head>
	<title>{data.series.name} - Alexandria</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Back button -->
	<a
		href="/series"
		class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6"
	>
		<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
		</svg>
		All Series
	</a>

	<!-- Series header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
			{data.series.name}
		</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-2">
			{data.series.books.length} {data.series.books.length === 1 ? 'book' : 'books'}
			{#if data.series.authors.length > 0}
				<span class="mx-2">·</span>
				{data.series.authors.join(', ')}
			{/if}
		</p>
	</div>

	<!-- Books grid - ordered by series index -->
	{#if data.series.books.length === 0}
		<div class="text-center py-12">
			<p class="text-gray-500 dark:text-gray-400">No books found</p>
		</div>
	{:else}
		<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
			{#each data.series.books as item (item.id)}
				<BookCard {item} />
			{/each}
		</div>
	{/if}
</div>
