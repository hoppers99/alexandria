<script lang="ts">
	import BookCard from '$lib/components/BookCard.svelte';
	import { formatBytes, type ItemSummary, type LibraryStats, type CurrentlyReadingItem } from '$lib/api';

	interface Props {
		data: {
			recentItems: ItemSummary[];
			stats: LibraryStats;
			currentlyReading: CurrentlyReadingItem[];
		};
	}

	let { data }: Props = $props();

	// Format relative time
	function formatRelativeTime(isoDate: string): string {
		const date = new Date(isoDate);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / (1000 * 60));
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffMins < 1) return 'Just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString();
	}
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Library stats -->
	<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
		<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
			<div class="text-2xl font-bold text-gray-900 dark:text-white">{data.stats.total_items.toLocaleString()}</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">Books</div>
		</div>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
			<div class="text-2xl font-bold text-gray-900 dark:text-white">{data.stats.total_authors.toLocaleString()}</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">Authors</div>
		</div>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
			<div class="text-2xl font-bold text-gray-900 dark:text-white">{data.stats.total_series}</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">Series</div>
		</div>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
			<div class="text-2xl font-bold text-gray-900 dark:text-white">{formatBytes(data.stats.total_size_bytes)}</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">Total Size</div>
		</div>
	</div>

	<!-- Format breakdown -->
	<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm mb-8">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Formats</h2>
		<div class="flex flex-wrap gap-2">
			{#each Object.entries(data.stats.formats) as [format, count]}
				<span class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm">
					{format.toUpperCase()}: {count.toLocaleString()}
				</span>
			{/each}
		</div>
	</div>

	<!-- Currently Reading -->
	{#if data.currentlyReading && data.currentlyReading.length > 0}
		<section class="mb-8">
			<div class="flex justify-between items-center mb-4">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Currently Reading</h2>
			</div>

			<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
				{#each data.currentlyReading as reading (reading.item.id)}
					<div class="relative">
						<BookCard item={reading.item} progress={reading.progress} />
						<div class="mt-1 text-xs text-gray-500 dark:text-gray-400 text-center">
							{Math.round(reading.progress * 100)}% · {formatRelativeTime(reading.last_read_at)}
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Recently added -->
	<section>
		<div class="flex justify-between items-center mb-4">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Recently Added</h2>
			<a href="/browse" class="text-blue-600 dark:text-blue-400 text-sm hover:underline">
				View all &rarr;
			</a>
		</div>

		<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
			{#each data.recentItems as item (item.id)}
				<BookCard {item} />
			{/each}
		</div>
	</section>

	<!-- Migration status (if active) -->
	{#if data.stats.migration_status && data.stats.migration_status.pending > 0}
		<section class="mt-8">
			<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
				<h3 class="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Migration in Progress</h3>
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
					<div>
						<span class="text-yellow-600 dark:text-yellow-400">Migrated:</span>
						<span class="font-medium text-yellow-800 dark:text-yellow-200">{data.stats.migration_status.migrated?.toLocaleString() ?? 0}</span>
					</div>
					<div>
						<span class="text-yellow-600 dark:text-yellow-400">Pending:</span>
						<span class="font-medium text-yellow-800 dark:text-yellow-200">{data.stats.migration_status.pending?.toLocaleString() ?? 0}</span>
					</div>
					<div>
						<span class="text-yellow-600 dark:text-yellow-400">Duplicates:</span>
						<span class="font-medium text-yellow-800 dark:text-yellow-200">{data.stats.migration_status.duplicate?.toLocaleString() ?? 0}</span>
					</div>
					<div>
						<span class="text-yellow-600 dark:text-yellow-400">Failed:</span>
						<span class="font-medium text-yellow-800 dark:text-yellow-200">{data.stats.migration_status.failed?.toLocaleString() ?? 0}</span>
					</div>
				</div>
			</div>
		</section>
	{/if}
</div>
