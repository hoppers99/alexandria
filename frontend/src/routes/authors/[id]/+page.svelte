<script lang="ts">
	import BookCard from '$lib/components/BookCard.svelte';
	import type { AuthorDetail, PaginatedItems } from '$lib/api';

	interface Props {
		data: {
			author: AuthorDetail;
			books: PaginatedItems;
			page: number;
		};
	}

	let { data }: Props = $props();

	function buildUrl(page: number) {
		return `/authors/${data.author.id}?page=${page}`;
	}
</script>

<svelte:head>
	<title>{data.author.name} - Alexandria</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Back button -->
	<a
		href="/authors"
		class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6"
	>
		<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
		</svg>
		All Authors
	</a>

	<!-- Author header -->
	<div class="flex items-start gap-6 mb-8">
		{#if data.author.photo_url}
			<img
				src={data.author.photo_url}
				alt={data.author.name}
				class="w-32 h-32 rounded-full object-cover"
			/>
		{:else}
			<div
				class="w-32 h-32 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center"
			>
				<span class="text-4xl text-gray-400 dark:text-gray-500">
					{data.author.name.charAt(0).toUpperCase()}
				</span>
			</div>
		{/if}

		<div>
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
				{data.author.name}
			</h1>
			<p class="text-gray-500 dark:text-gray-400 mt-1">
				{data.books.total} {data.books.total === 1 ? 'book' : 'books'}
			</p>
			{#if data.author.bio}
				<p class="mt-4 text-gray-700 dark:text-gray-300 max-w-2xl">
					{data.author.bio}
				</p>
			{/if}
		</div>
	</div>

	<!-- Books grid -->
	<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Books</h2>

	{#if data.books.items.length === 0}
		<div class="text-center py-12">
			<p class="text-gray-500 dark:text-gray-400">No books found</p>
		</div>
	{:else}
		<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
			{#each data.books.items as item (item.id)}
				<BookCard {item} />
			{/each}
		</div>
	{/if}

	<!-- Pagination -->
	{#if data.books.pages > 1}
		<nav class="mt-8 flex justify-center">
			<div class="flex items-center gap-1">
				{#if data.page > 1}
					<a
						href={buildUrl(data.page - 1)}
						class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
					>
						Previous
					</a>
				{/if}

				{#each Array.from({ length: Math.min(data.books.pages, 7) }, (_, i) => {
					if (data.books.pages <= 7) return i + 1;
					if (data.page <= 4) return i + 1;
					if (data.page >= data.books.pages - 3) return data.books.pages - 6 + i;
					return data.page - 3 + i;
				}) as pageNum}
					<a
						href={buildUrl(pageNum)}
						class="px-3 py-2 border rounded-lg {pageNum === data.page
							? 'bg-blue-600 text-white border-blue-600'
							: 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						{pageNum}
					</a>
				{/each}

				{#if data.page < data.books.pages}
					<a
						href={buildUrl(data.page + 1)}
						class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
					>
						Next
					</a>
				{/if}
			</div>
		</nav>

		<p class="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
			Page {data.page} of {data.books.pages}
		</p>
	{/if}
</div>
