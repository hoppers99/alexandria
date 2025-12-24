<script lang="ts">
	import BookCard from '$lib/components/BookCard.svelte';
	import type { ItemSummary } from '$lib/api';

	interface Props {
		data: {
			items: ItemSummary[];
			total: number;
			page: number;
			per_page: number;
			pages: number;
			sort: string;
			order: string;
			q?: string;
			format?: string;
			media_type?: string;
		};
	}

	let { data }: Props = $props();

	function buildUrl(params: Record<string, string | number | undefined>) {
		const searchParams = new URLSearchParams();
		for (const [key, value] of Object.entries(params)) {
			if (value !== undefined && value !== '') {
				searchParams.set(key, String(value));
			}
		}
		return `/browse?${searchParams}`;
	}
</script>

<svelte:head>
	<title>Browse - Alexandria</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header with filters -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
			Library
			<span class="text-gray-500 dark:text-gray-400 font-normal text-lg">
				({data.total.toLocaleString()} books)
			</span>
		</h1>

		<div class="flex flex-wrap gap-2">
			<!-- Sort -->
			<select
				class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
				onchange={(e) => window.location.href = buildUrl({ ...data, sort: e.currentTarget.value, page: 1 })}
			>
				<option value="date_added" selected={data.sort === 'date_added'}>Date Added</option>
				<option value="title" selected={data.sort === 'title'}>Title</option>
				<option value="series_name" selected={data.sort === 'series_name'}>Series</option>
			</select>

			<!-- Order -->
			<select
				class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
				onchange={(e) => window.location.href = buildUrl({ ...data, order: e.currentTarget.value, page: 1 })}
			>
				<option value="desc" selected={data.order === 'desc'}>Newest First</option>
				<option value="asc" selected={data.order === 'asc'}>Oldest First</option>
			</select>

			<!-- Media type filter -->
			<select
				class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
				onchange={(e) => window.location.href = buildUrl({ ...data, media_type: e.currentTarget.value || undefined, page: 1 })}
			>
				<option value="" selected={!data.media_type}>All Types</option>
				<option value="fiction" selected={data.media_type === 'fiction'}>Fiction</option>
				<option value="non-fiction" selected={data.media_type === 'non-fiction'}>Non-Fiction</option>
			</select>

			<!-- Format filter -->
			<select
				class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
				onchange={(e) => window.location.href = buildUrl({ ...data, format: e.currentTarget.value || undefined, page: 1 })}
			>
				<option value="" selected={!data.format}>All Formats</option>
				<option value="epub" selected={data.format === 'epub'}>EPUB</option>
				<option value="pdf" selected={data.format === 'pdf'}>PDF</option>
				<option value="mobi" selected={data.format === 'mobi'}>MOBI</option>
			</select>
		</div>
	</div>

	<!-- Search results info -->
	{#if data.q}
		<div class="mb-4 text-gray-600 dark:text-gray-400">
			Showing results for "<span class="font-medium">{data.q}</span>"
			<a href="/browse" class="text-blue-600 dark:text-blue-400 ml-2 hover:underline">Clear</a>
		</div>
	{/if}

	<!-- Book grid -->
	{#if data.items.length === 0}
		<div class="text-center py-12">
			<p class="text-gray-500 dark:text-gray-400">No books found</p>
		</div>
	{:else}
		<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
			{#each data.items as item (item.id)}
				<BookCard {item} />
			{/each}
		</div>
	{/if}

	<!-- Pagination -->
	{#if data.pages > 1}
		<nav class="mt-8 flex justify-center">
			<div class="flex items-center gap-1">
				{#if data.page > 1}
					<a
						href={buildUrl({ ...data, page: data.page - 1 })}
						class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
					>
						Previous
					</a>
				{/if}

				{#each Array.from({ length: Math.min(data.pages, 7) }, (_, i) => {
					// Show pages around current page
					if (data.pages <= 7) return i + 1;
					if (data.page <= 4) return i + 1;
					if (data.page >= data.pages - 3) return data.pages - 6 + i;
					return data.page - 3 + i;
				}) as pageNum}
					<a
						href={buildUrl({ ...data, page: pageNum })}
						class="px-3 py-2 border rounded-lg {pageNum === data.page
							? 'bg-blue-600 text-white border-blue-600'
							: 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						{pageNum}
					</a>
				{/each}

				{#if data.page < data.pages}
					<a
						href={buildUrl({ ...data, page: data.page + 1 })}
						class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
					>
						Next
					</a>
				{/if}
			</div>
		</nav>

		<p class="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
			Page {data.page} of {data.pages}
		</p>
	{/if}
</div>
