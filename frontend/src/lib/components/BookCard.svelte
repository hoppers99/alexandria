<script lang="ts">
	import type { ItemSummary } from '$lib/api';

	interface Props {
		item: ItemSummary;
	}

	let { item }: Props = $props();

	const authorsText = $derived(item.authors.slice(0, 2).join(', ') + (item.authors.length > 2 ? '...' : ''));

	// Format badge colours
	const formatColors: Record<string, string> = {
		epub: 'bg-green-600',
		mobi: 'bg-orange-600',
		pdf: 'bg-red-600',
		azw: 'bg-yellow-600',
		azw3: 'bg-yellow-600',
		cbz: 'bg-purple-600',
		fb2: 'bg-blue-600'
	};
</script>

<a
	href="/book/{item.id}"
	class="group block bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden"
>
	<div class="aspect-[2/3] bg-gray-200 dark:bg-gray-700" style="position: relative;">
		{#if item.cover_url}
			<img
				src={item.cover_url}
				alt={item.title}
				class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
				loading="lazy"
			/>
		{:else}
			<div class="w-full h-full flex items-center justify-center p-4">
				<span class="text-gray-400 dark:text-gray-500 text-center text-sm leading-tight">
					{item.title}
				</span>
			</div>
		{/if}

		{#if item.formats && item.formats.length > 0}
			<div
				class="flex gap-1"
				style="position: absolute; bottom: 0.5rem; right: 0.5rem; z-index: 10;"
			>
				{#each item.formats as format}
					<span
						class="text-white text-xs px-2 py-1 rounded uppercase"
						style="background: {format === 'epub' ? '#16a34a' : format === 'mobi' ? '#ea580c' : format === 'pdf' ? '#dc2626' : format === 'azw' || format === 'azw3' ? '#ca8a04' : format === 'cbz' ? '#9333ea' : format === 'fb2' ? '#2563eb' : '#4b5563'};"
					>
						{format}
					</span>
				{/each}
			</div>
		{/if}
	</div>

	<div class="p-3">
		<h3 class="font-medium text-gray-900 dark:text-white line-clamp-2 text-sm leading-tight">
			{item.title}
		</h3>
		{#if authorsText}
			<p class="text-gray-500 dark:text-gray-400 text-xs mt-1 line-clamp-1">
				{authorsText}
			</p>
		{/if}
		{#if item.series_name}
			<p class="text-blue-600 dark:text-blue-400 text-xs mt-1 line-clamp-1">
				{item.series_name}
			</p>
		{/if}
	</div>
</a>
