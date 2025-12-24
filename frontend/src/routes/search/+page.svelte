<script lang="ts">
	import BookCard from '$lib/components/BookCard.svelte';
	import type { PaginatedItems, PaginatedAuthors, PaginatedSeries } from '$lib/api';

	interface Props {
		data: {
			q: string;
			page?: number;
			items: PaginatedItems | null;
			authors: PaginatedAuthors | null;
			series: PaginatedSeries | null;
		};
	}

	let { data }: Props = $props();
	let searchQuery = $state(data.q);

	function buildUrl(page: number) {
		return `/search?q=${encodeURIComponent(data.q)}&page=${page}`;
	}
</script>

<svelte:head>
	<title>{data.q ? `Search: ${data.q}` : 'Search'} - Alexandria</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Search form -->
	<form action="/search" method="GET" class="mb-8">
		<div class="flex gap-2">
			<div class="relative flex-1">
				<input
					type="search"
					name="q"
					bind:value={searchQuery}
					placeholder="Search books, authors, or series..."
					class="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
					autofocus
				/>
				<svg
					class="absolute left-3 top-3.5 w-5 h-5 text-gray-400"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
					/>
				</svg>
			</div>
			<button
				type="submit"
				class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
			>
				Search
			</button>
		</div>
	</form>

	{#if !data.q}
		<!-- Empty state -->
		<div class="text-center py-16">
			<svg
				class="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
				/>
			</svg>
			<h2 class="text-xl font-medium text-gray-600 dark:text-gray-400">
				Search your library
			</h2>
			<p class="text-gray-500 dark:text-gray-500 mt-2">
				Find books by title, description, author, or series name
			</p>
		</div>
	{:else}
		<!-- Results header -->
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
			Results for "<span class="text-blue-600 dark:text-blue-400">{data.q}</span>"
		</h1>

		<!-- Authors section (if any matches) -->
		{#if data.authors && data.authors.authors.length > 0}
			<section class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						Authors ({data.authors.total})
					</h2>
					{#if data.authors.total > 10}
						<a
							href="/authors?q={encodeURIComponent(data.q)}"
							class="text-blue-600 dark:text-blue-400 text-sm hover:underline"
						>
							View all
						</a>
					{/if}
				</div>
				<div class="flex flex-wrap gap-2">
					{#each data.authors.authors as author (author.id)}
						<a
							href="/authors/{author.id}"
							class="inline-flex items-center px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
						>
							<span class="font-medium text-gray-900 dark:text-white">{author.name}</span>
							<span class="ml-2 text-sm text-gray-500 dark:text-gray-400">
								({author.book_count})
							</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Series section (if any matches) -->
		{#if data.series && data.series.series.length > 0}
			<section class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						Series ({data.series.total})
					</h2>
					{#if data.series.total > 10}
						<a
							href="/series?q={encodeURIComponent(data.q)}"
							class="text-blue-600 dark:text-blue-400 text-sm hover:underline"
						>
							View all
						</a>
					{/if}
				</div>
				<div class="flex flex-wrap gap-2">
					{#each data.series.series as s (s.name)}
						<a
							href="/series/{encodeURIComponent(s.name)}"
							class="inline-flex items-center px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
						>
							<span class="font-medium text-gray-900 dark:text-white">{s.name}</span>
							<span class="ml-2 text-sm text-gray-500 dark:text-gray-400">
								({s.book_count} books)
							</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Books section -->
		{#if data.items}
			<section>
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
					Books ({data.items.total})
				</h2>

				{#if data.items.items.length === 0}
					<div class="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
						<p class="text-gray-500 dark:text-gray-400">No books found matching your search</p>
					</div>
				{:else}
					<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
						{#each data.items.items as item (item.id)}
							<BookCard {item} />
						{/each}
					</div>

					<!-- Pagination for books -->
					{#if data.items.pages > 1}
						<nav class="mt-8 flex justify-center">
							<div class="flex items-center gap-1">
								{#if (data.page ?? 1) > 1}
									<a
										href={buildUrl((data.page ?? 1) - 1)}
										class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
									>
										Previous
									</a>
								{/if}

								{#each Array.from({ length: Math.min(data.items.pages, 7) }, (_, i) => {
									const currentPage = data.page ?? 1;
									if (data.items && data.items.pages <= 7) return i + 1;
									if (currentPage <= 4) return i + 1;
									if (data.items && currentPage >= data.items.pages - 3)
										return data.items.pages - 6 + i;
									return currentPage - 3 + i;
								}) as pageNum}
									<a
										href={buildUrl(pageNum)}
										class="px-3 py-2 border rounded-lg {pageNum === (data.page ?? 1)
											? 'bg-blue-600 text-white border-blue-600'
											: 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
									>
										{pageNum}
									</a>
								{/each}

								{#if (data.page ?? 1) < data.items.pages}
									<a
										href={buildUrl((data.page ?? 1) + 1)}
										class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
									>
										Next
									</a>
								{/if}
							</div>
						</nav>

						<p class="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
							Page {data.page ?? 1} of {data.items.pages}
						</p>
					{/if}
				{/if}
			</section>
		{/if}

		<!-- No results at all -->
		{#if data.items?.items.length === 0 && data.authors?.authors.length === 0 && data.series?.series.length === 0}
			<div class="text-center py-16">
				<svg
					class="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<h2 class="text-xl font-medium text-gray-600 dark:text-gray-400">No results found</h2>
				<p class="text-gray-500 dark:text-gray-500 mt-2">
					Try a different search term or browse the library
				</p>
				<a
					href="/browse"
					class="inline-block mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
				>
					Browse Library
				</a>
			</div>
		{/if}
	{/if}
</div>
