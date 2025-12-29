<script lang="ts">
	import type { ItemSummary } from '$lib/api';

	interface Props {
		item: ItemSummary;
		progress?: number; // 0.0 to 1.0
		pileColor?: string | null; // Explicit override for pile colour
	}

	let { item, progress, pileColor }: Props = $props();

	const authorsText = $derived(item.authors.slice(0, 2).join(', ') + (item.authors.length > 2 ? '...' : ''));
	const progressPercent = $derived(progress ? Math.round(progress * 100) : 0);

	// Format series index for display (e.g. 1, 2.5, 10)
	const seriesIndexDisplay = $derived.by(() => {
		if (!item.series_index) return null;
		// Show as integer if it's a whole number, otherwise one decimal
		return item.series_index % 1 === 0
			? item.series_index.toString()
			: item.series_index.toFixed(1);
	});

	// Derive pile colour: explicit prop > first system pile with colour > first pile with colour
	const effectivePileColor = $derived.by(() => {
		if (pileColor) return pileColor;
		if (!item.piles || item.piles.length === 0) return null;
		// Prefer system piles (To Read, Currently Reading, Read)
		const systemPile = item.piles.find((p) => p.is_system && p.color);
		if (systemPile) return systemPile.color;
		// Fall back to first pile with a colour
		const anyPile = item.piles.find((p) => p.color);
		return anyPile?.color ?? null;
	});

	// Darken a hex colour for the border
	function darkenColor(hex: string, percent: number = 15): string {
		const num = parseInt(hex.replace('#', ''), 16);
		const r = Math.max(0, (num >> 16) - Math.round(255 * percent / 100));
		const g = Math.max(0, ((num >> 8) & 0x00FF) - Math.round(255 * percent / 100));
		const b = Math.max(0, (num & 0x0000FF) - Math.round(255 * percent / 100));
		return `#${(r << 16 | g << 8 | b).toString(16).padStart(6, '0')}`;
	}

	// Lighten a hex colour for gradient highlight
	function lightenColor(hex: string, percent: number = 20): string {
		const num = parseInt(hex.replace('#', ''), 16);
		const r = Math.min(255, (num >> 16) + Math.round(255 * percent / 100));
		const g = Math.min(255, ((num >> 8) & 0x00FF) + Math.round(255 * percent / 100));
		const b = Math.min(255, (num & 0x0000FF) + Math.round(255 * percent / 100));
		return `#${(r << 16 | g << 8 | b).toString(16).padStart(6, '0')}`;
	}

	const bookmarkBorderColor = $derived(effectivePileColor ? darkenColor(effectivePileColor, 25) : null);
	const bookmarkHighlightColor = $derived(effectivePileColor ? lightenColor(effectivePileColor, 15) : null);
	const bookmarkGradientId = $derived(effectivePileColor ? `bookmark-gradient-${item.id}` : null);

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

		<!-- Series index badge -->
		{#if seriesIndexDisplay}
			<div
				class="absolute top-1.5 left-1.5 bg-black/70 text-white text-xs font-medium px-1.5 py-0.5 rounded"
				style="z-index: 15;"
				title="{item.series_name} #{seriesIndexDisplay}"
			>
				#{seriesIndexDisplay}
			</div>
		{/if}

		<!-- Pile bookmark indicator -->
		{#if effectivePileColor}
			<div class="absolute top-0 right-2" style="z-index: 15;">
				<svg width="16" height="26" viewBox="0 0 16 26" class="drop-shadow-md">
					<!-- Gradient definition -->
					<defs>
						<linearGradient id={bookmarkGradientId} x1="0%" y1="0%" x2="100%" y2="0%">
							<stop offset="0%" stop-color={bookmarkHighlightColor} />
							<stop offset="35%" stop-color={effectivePileColor} />
							<stop offset="100%" stop-color={bookmarkBorderColor} />
						</linearGradient>
					</defs>
					<!-- Bookmark shape with gradient fill and defined edges -->
					<path
						d="M0 0 L16 0 L16 22 L8 18 L0 22 Z"
						fill="url(#{bookmarkGradientId})"
						stroke={bookmarkBorderColor}
						stroke-width="1.5"
						stroke-linejoin="round"
					/>
				</svg>
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

		{#if progress !== undefined && progress > 0}
			<!-- Progress bar -->
			<div class="absolute bottom-0 left-0 right-0 h-1.5 bg-black/40" style="z-index: 10;">
				<div
					class="h-full bg-blue-500 transition-all duration-300"
					style="width: {progressPercent}%;"
				></div>
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
