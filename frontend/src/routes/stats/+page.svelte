<script lang="ts">
	import type { LibraryStats, ReadingStats } from '$lib/api';
	import { formatBytes } from '$lib/api';

	interface Props {
		data: {
			libraryStats: LibraryStats;
			readingStats: ReadingStats;
		};
	}

	let { data }: Props = $props();

	// Calculate percentage of books read
	const readPercentage = $derived(
		data.readingStats.total_books > 0
			? Math.round((data.readingStats.books_read / data.readingStats.total_books) * 100)
			: 0
	);

	// Get max value for bar chart scaling
	const maxMonthlyReads = $derived(
		Math.max(...data.readingStats.monthly_reads.map((m) => m.count), 1)
	);

	// Format month for display (e.g., "2024-01" -> "Jan 2024")
	function formatMonth(monthStr: string): string {
		const [year, month] = monthStr.split('-');
		const date = new Date(parseInt(year), parseInt(month) - 1);
		return date.toLocaleDateString('en-NZ', { month: 'short', year: 'numeric' });
	}

	// Format short month (e.g., "2024-01" -> "Jan")
	function formatShortMonth(monthStr: string): string {
		const [year, month] = monthStr.split('-');
		const date = new Date(parseInt(year), parseInt(month) - 1);
		return date.toLocaleDateString('en-NZ', { month: 'short' });
	}
</script>

<svelte:head>
	<title>Statistics - Alexandria</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-8">Library Statistics</h1>

	<!-- Reading Overview Cards -->
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
		<!-- Books Read -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			<div class="flex items-center">
				<div class="flex-shrink-0 p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
					<svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
				</div>
				<div class="ml-4">
					<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Books Read</p>
					<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.readingStats.books_read}</p>
				</div>
			</div>
		</div>

		<!-- Currently Reading -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			<div class="flex items-center">
				<div class="flex-shrink-0 p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
					<svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
					</svg>
				</div>
				<div class="ml-4">
					<p class="text-sm font-medium text-gray-500 dark:text-gray-400">In Progress</p>
					<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.readingStats.books_in_progress}</p>
				</div>
			</div>
		</div>

		<!-- Reading Streak -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			<div class="flex items-center">
				<div class="flex-shrink-0 p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
					<svg class="w-6 h-6 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
					</svg>
				</div>
				<div class="ml-4">
					<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Reading Streak</p>
					<p class="text-2xl font-bold text-gray-900 dark:text-white">
						{data.readingStats.reading_streak_days}
						<span class="text-sm font-normal text-gray-500 dark:text-gray-400">days</span>
					</p>
				</div>
			</div>
		</div>

		<!-- Read This Year -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			<div class="flex items-center">
				<div class="flex-shrink-0 p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
					<svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
					</svg>
				</div>
				<div class="ml-4">
					<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Read This Year</p>
					<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.readingStats.read_this_year}</p>
				</div>
			</div>
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
		<!-- Reading Progress Overview -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Library Overview</h2>
			<div class="space-y-4">
				<div>
					<div class="flex justify-between text-sm mb-1">
						<span class="text-gray-600 dark:text-gray-400">Read</span>
						<span class="text-gray-900 dark:text-white font-medium">{data.readingStats.books_read} of {data.readingStats.total_books}</span>
					</div>
					<div class="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
						<div
							class="h-full bg-green-500 transition-all duration-500"
							style="width: {readPercentage}%"
						></div>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{readPercentage}% of your library</p>
				</div>

				<div class="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="text-center">
						<p class="text-2xl font-bold text-green-600 dark:text-green-400">{data.readingStats.books_read}</p>
						<p class="text-xs text-gray-500 dark:text-gray-400">Read</p>
					</div>
					<div class="text-center">
						<p class="text-2xl font-bold text-blue-600 dark:text-blue-400">{data.readingStats.books_in_progress}</p>
						<p class="text-xs text-gray-500 dark:text-gray-400">In Progress</p>
					</div>
					<div class="text-center">
						<p class="text-2xl font-bold text-gray-600 dark:text-gray-400">{data.readingStats.books_not_started}</p>
						<p class="text-xs text-gray-500 dark:text-gray-400">Not Started</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Recent Finishes -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recently Finished</h2>
			{#if data.readingStats.recent_finishes.length > 0}
				<ul class="space-y-3">
					{#each data.readingStats.recent_finishes as book}
						<li class="flex items-center justify-between">
							<a
								href="/book/{book.item_id}"
								class="text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 truncate flex-1 mr-4"
							>
								{book.title}
							</a>
							<span class="text-sm text-gray-500 dark:text-gray-400 flex-shrink-0">
								{book.finished_at ? new Date(book.finished_at).toLocaleDateString() : ''}
							</span>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-gray-500 dark:text-gray-400 text-sm">No books finished yet. Start reading!</p>
			{/if}
		</div>
	</div>

	<!-- Monthly Reading Chart -->
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Books Finished by Month</h2>
		<div class="h-48 flex items-end justify-between gap-2">
			{#each data.readingStats.monthly_reads as month}
				<div class="flex-1 flex flex-col items-center">
					<div
						class="w-full bg-blue-500 dark:bg-blue-400 rounded-t transition-all duration-500 min-h-[4px]"
						style="height: {(month.count / maxMonthlyReads) * 100}%"
						title="{formatMonth(month.month)}: {month.count} books"
					></div>
					<span class="text-xs text-gray-500 dark:text-gray-400 mt-2 rotate-0 whitespace-nowrap">
						{formatShortMonth(month.month)}
					</span>
				</div>
			{/each}
		</div>
		{#if data.readingStats.monthly_reads.every(m => m.count === 0)}
			<p class="text-center text-gray-500 dark:text-gray-400 text-sm mt-4">
				No books finished in the past 12 months
			</p>
		{/if}
	</div>

	<!-- Library Statistics -->
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Library Details</h2>
		<div class="grid grid-cols-2 sm:grid-cols-4 gap-6">
			<div>
				<p class="text-sm text-gray-500 dark:text-gray-400">Total Books</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.libraryStats.total_items}</p>
			</div>
			<div>
				<p class="text-sm text-gray-500 dark:text-gray-400">Total Files</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.libraryStats.total_files}</p>
			</div>
			<div>
				<p class="text-sm text-gray-500 dark:text-gray-400">Authors</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.libraryStats.total_authors}</p>
			</div>
			<div>
				<p class="text-sm text-gray-500 dark:text-gray-400">Series</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{data.libraryStats.total_series}</p>
			</div>
		</div>

		<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
			<div class="flex flex-wrap gap-6">
				<div>
					<p class="text-sm text-gray-500 dark:text-gray-400 mb-2">Total Size</p>
					<p class="text-lg font-semibold text-gray-900 dark:text-white">
						{formatBytes(data.libraryStats.total_size_bytes)}
					</p>
				</div>

				{#if Object.keys(data.libraryStats.formats).length > 0}
					<div class="flex-1 min-w-[200px]">
						<p class="text-sm text-gray-500 dark:text-gray-400 mb-2">Formats</p>
						<div class="flex flex-wrap gap-2">
							{#each Object.entries(data.libraryStats.formats).sort((a, b) => b[1] - a[1]) as [format, count]}
								<span class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-sm">
									{format.toUpperCase()}: {count}
								</span>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
