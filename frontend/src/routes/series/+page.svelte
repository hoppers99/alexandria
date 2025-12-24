<script lang="ts">
	import type { SeriesSummary } from '$lib/api';

	interface Props {
		data: {
			series: SeriesSummary[];
			total: number;
			page: number;
			per_page: number;
			pages: number;
			sort: string;
			order: string;
			q?: string;
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
		return `/series?${searchParams}`;
	}
</script>

<svelte:head>
	<title>Series - Alexandria</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header with filters -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
			Series
			<span class="text-gray-500 dark:text-gray-400 font-normal text-lg">
				({data.total.toLocaleString()})
			</span>
		</h1>

		<div class="flex flex-wrap gap-2">
			<!-- Sort -->
			<select
				class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
				onchange={(e) => (window.location.href = buildUrl({ ...data, sort: e.currentTarget.value, page: 1 }))}
			>
				<option value="name" selected={data.sort === 'name'}>Name</option>
				<option value="book_count" selected={data.sort === 'book_count'}>Book Count</option>
			</select>

			<!-- Order -->
			<select
				class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
				onchange={(e) => (window.location.href = buildUrl({ ...data, order: e.currentTarget.value, page: 1 }))}
			>
				<option value="asc" selected={data.order === 'asc'}>A-Z</option>
				<option value="desc" selected={data.order === 'desc'}>Z-A</option>
			</select>
		</div>
	</div>

	<!-- Search results info -->
	{#if data.q}
		<div class="mb-4 text-gray-600 dark:text-gray-400">
			Showing results for "<span class="font-medium">{data.q}</span>"
			<a href="/series" class="text-blue-600 dark:text-blue-400 ml-2 hover:underline">Clear</a>
		</div>
	{/if}

	<!-- Series grid -->
	{#if data.series.length === 0}
		<div class="text-center py-12">
			<p class="text-gray-500 dark:text-gray-400">No series found</p>
		</div>
	{:else}
		<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
			{#each data.series as series (series.name)}
				<a
					href="/series/{encodeURIComponent(series.name)}"
					class="group block"
				>
					<div class="aspect-[2/3] bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden shadow-md group-hover:shadow-lg transition-shadow">
						{#if series.first_cover_url}
							<img
								src={series.first_cover_url}
								alt={series.name}
								class="w-full h-full object-cover"
							/>
						{:else}
							<div class="w-full h-full flex items-center justify-center p-2">
								<span class="text-gray-400 dark:text-gray-500 text-center text-sm">
									{series.name}
								</span>
							</div>
						{/if}
					</div>
					<h2 class="mt-2 font-medium text-gray-900 dark:text-white text-sm truncate group-hover:text-blue-600 dark:group-hover:text-blue-400">
						{series.name}
					</h2>
					<p class="text-xs text-gray-500 dark:text-gray-400 truncate">
						{series.authors.join(', ')}
					</p>
					<p class="text-xs text-gray-400 dark:text-gray-500">
						{series.book_count} {series.book_count === 1 ? 'book' : 'books'}
					</p>
				</a>
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
