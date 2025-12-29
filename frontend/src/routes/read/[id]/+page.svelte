<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { getReadingProgress, updateReadingProgress, type ItemDetail } from '$lib/api';

	interface Props {
		data: {
			item: ItemDetail;
			readableFileId: number;
			readableFormat: string;
		};
	}

	let { data }: Props = $props();

	let readerContainer: HTMLDivElement;
	let view: any = $state(null);
	let book: any = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);
	let currentFraction = $state(0);
	let currentLocation = $state('');
	let currentCfi: string | null = $state(null);
	let sidebarOpen = $state(false);
	let toc: any[] = $state([]);
	let settings = $state({
		flow: 'paginated',
		spacing: 1.4,
		justify: true,
		hyphenate: true
	});

	// Progress saving state
	let lastSavedFraction = 0;
	let saveTimeout: ReturnType<typeof setTimeout> | null = null;
	let initialLocationToRestore: string | null = null;

	// Store IDs to avoid closure capture issues with reactive props
	const itemId = data.item.id;
	const fileId = data.readableFileId;
	const bookUrl = `/api/items/${itemId}/files/${fileId}/download`;

	// Save progress to the server (debounced)
	function saveProgress() {
		if (saveTimeout) clearTimeout(saveTimeout);

		// Capture current values before the timeout
		const fraction = currentFraction;
		const cfi = currentCfi;
		const location = currentLocation;

		saveTimeout = setTimeout(async () => {
			// Only save if progress changed significantly (>1%)
			if (Math.abs(fraction - lastSavedFraction) < 0.01) return;

			try {
				await updateReadingProgress(
					itemId,
					fileId,
					fraction,
					cfi ?? undefined,
					location || undefined
				);
				lastSavedFraction = fraction;
			} catch (e) {
				console.error('Failed to save reading progress:', e);
			}
		}, 2000); // Debounce 2 seconds
	}

	// Save progress immediately (for when leaving page)
	async function saveProgressNow() {
		if (saveTimeout) clearTimeout(saveTimeout);
		if (Math.abs(currentFraction - lastSavedFraction) < 0.001) return;

		try {
			await updateReadingProgress(
				itemId,
				fileId,
				currentFraction,
				currentCfi ?? undefined,
				currentLocation || undefined
			);
		} catch (e) {
			console.error('Failed to save reading progress:', e);
		}
	}

	function getReaderCSS() {
		return `
			@namespace epub "http://www.idpf.org/2007/ops";
			html {
				color-scheme: light dark;
			}
			@media (prefers-color-scheme: dark) {
				a:link {
					color: lightblue;
				}
			}
			p, li, blockquote, dd {
				line-height: ${settings.spacing};
				text-align: ${settings.justify ? 'justify' : 'start'};
				-webkit-hyphens: ${settings.hyphenate ? 'auto' : 'manual'};
				hyphens: ${settings.hyphenate ? 'auto' : 'manual'};
				-webkit-hyphenate-limit-before: 3;
				-webkit-hyphenate-limit-after: 2;
				-webkit-hyphenate-limit-lines: 2;
				hanging-punctuation: allow-end last;
				widows: 2;
			}
			[align="left"] { text-align: left; }
			[align="right"] { text-align: right; }
			[align="center"] { text-align: center; }
			[align="justify"] { text-align: justify; }
			pre {
				white-space: pre-wrap !important;
			}
			aside[epub|type~="endnote"],
			aside[epub|type~="footnote"],
			aside[epub|type~="note"],
			aside[epub|type~="rearnote"] {
				display: none;
			}
		`;
	}

	onMount(async () => {
		if (!browser) return;

		try {
			// Load saved progress first
			try {
				const progressResponse = await getReadingProgress(itemId);
				if (progressResponse.progress?.location) {
					initialLocationToRestore = progressResponse.progress.location;
					lastSavedFraction = progressResponse.progress.progress;
				}
			} catch (e) {
				console.warn('Could not load reading progress:', e);
			}

			// Dynamically import foliate-js (it's an ES module)
			await import('foliate-js/view.js');

			// Create the foliate-view custom element
			const foliateView = document.createElement('foliate-view');
			foliateView.style.cssText = 'width: 100%; height: 100%;';
			readerContainer.appendChild(foliateView);
			view = foliateView;

			// Open the book file
			await view.open(bookUrl);
			book = view.book;

			// Get table of contents
			if (book.toc) {
				toc = book.toc;
			}

			// Set up styles
			view.renderer.setStyles?.(getReaderCSS());

			// Set up event listeners
			view.addEventListener('relocate', (e: CustomEvent) => {
				const { fraction, location, tocItem, cfi } = e.detail;
				currentFraction = fraction;
				currentCfi = cfi || null;

				// Build a user-friendly location label
				if (tocItem?.label) {
					// Use chapter/section name if available
					currentLocation = tocItem.label;
				} else if (location?.current !== undefined && location?.total) {
					// Show "Page X of Y" style
					currentLocation = `Page ${location.current + 1} of ${location.total}`;
				} else if (location?.current !== undefined) {
					currentLocation = `Page ${location.current + 1}`;
				} else {
					currentLocation = `${Math.round(fraction * 100)}%`;
				}

				// Save progress after each navigation
				saveProgress();
			});

			view.addEventListener('load', (e: CustomEvent) => {
				// Add keyboard handler to the loaded document
				e.detail.doc.addEventListener('keydown', handleKeydown);
			});

			// Restore saved position or start at the beginning
			if (initialLocationToRestore) {
				try {
					await view.goTo(initialLocationToRestore);
				} catch (e) {
					console.warn('Could not restore reading position:', e);
					view.renderer.next();
				}
			} else {
				view.renderer.next();
			}

			loading = false;
		} catch (e) {
			console.error('Failed to load reader:', e);
			error = 'Failed to load the book. Please try again.';
			loading = false;
		}
	});

	// Save progress when leaving the page
	onDestroy(() => {
		saveProgressNow();
	});

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowLeft' || e.key === 'h') {
			view?.goLeft();
		} else if (e.key === 'ArrowRight' || e.key === 'l') {
			view?.goRight();
		} else if (e.key === 'Escape') {
			sidebarOpen = false;
		}
	}

	function goToTocItem(href: string) {
		view?.goTo(href);
		sidebarOpen = false;
	}

	function toggleFlow() {
		settings.flow = settings.flow === 'paginated' ? 'scrolled' : 'paginated';
		view?.renderer.setAttribute('flow', settings.flow);
	}
</script>

<svelte:head>
	<title>Reading: {data.item.title} - Alexandria</title>
</svelte:head>

<svelte:window on:keydown={handleKeydown} on:beforeunload={saveProgressNow} />

<div class="reader-wrapper">
	<!-- Top toolbar -->
	<header class="toolbar">
		<div class="toolbar-left">
			<button class="icon-button" onclick={() => (sidebarOpen = !sidebarOpen)} aria-label="Toggle table of contents">
				<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M4 6h16M4 12h16M4 18h16" />
				</svg>
			</button>
			<a href="/book/{data.item.id}" class="back-link" aria-label="Back to book details">
				<svg class="icon" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M15 19l-7-7 7-7" />
				</svg>
			</a>
		</div>

		<div class="toolbar-center">
			<span class="book-title">{data.item.title}</span>
		</div>

		<div class="toolbar-right">
			<button class="icon-button" onclick={toggleFlow} aria-label="Toggle layout">
				<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
					{#if settings.flow === 'paginated'}
						<rect x="3" y="3" width="7" height="18" rx="1" />
						<rect x="14" y="3" width="7" height="18" rx="1" />
					{:else}
						<rect x="3" y="3" width="18" height="18" rx="1" />
						<line x1="3" y1="9" x2="21" y2="9" />
						<line x1="3" y1="15" x2="21" y2="15" />
					{/if}
				</svg>
			</button>
		</div>
	</header>

	<!-- Sidebar (Table of Contents) -->
	{#if sidebarOpen}
		<div class="sidebar-overlay" onclick={() => (sidebarOpen = false)} aria-hidden="true"></div>
	{/if}
	<aside class="sidebar" class:open={sidebarOpen}>
		<div class="sidebar-header">
			<h2>Contents</h2>
			<button class="icon-button" onclick={() => (sidebarOpen = false)} aria-label="Close">
				<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>
		</div>
		<nav class="toc">
			{#if toc.length > 0}
				<ul>
					{#each toc as item}
						<li>
							<button class="toc-item" onclick={() => goToTocItem(item.href)}>
								{item.label}
							</button>
							{#if item.subitems?.length}
								<ul class="toc-subitems">
									{#each item.subitems as subitem}
										<li>
											<button class="toc-item" onclick={() => goToTocItem(subitem.href)}>
												{subitem.label}
											</button>
										</li>
									{/each}
								</ul>
							{/if}
						</li>
					{/each}
				</ul>
			{:else}
				<p class="toc-empty">No table of contents available</p>
			{/if}
		</nav>
	</aside>

	<!-- Main reader area -->
	<main class="reader-main">
		{#if loading}
			<div class="loading">
				<div class="spinner"></div>
				<p>Loading book...</p>
			</div>
		{:else if error}
			<div class="error">
				<p>{error}</p>
				<a href="/book/{data.item.id}" class="btn">Back to Book</a>
			</div>
		{/if}
		<div bind:this={readerContainer} class="reader-container" class:hidden={loading || error}></div>
	</main>

	<!-- Bottom navigation -->
	<footer class="nav-bar">
		<button class="nav-button" onclick={() => view?.goLeft()} aria-label="Previous page">
			<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M15 6L9 12l6 6" />
			</svg>
		</button>

		<div class="progress-container">
			<input
				type="range"
				class="progress-slider"
				min="0"
				max="1"
				step="any"
				value={currentFraction}
				oninput={(e) => view?.goToFraction(parseFloat(e.currentTarget.value))}
			/>
			<div class="progress-info">
				<span class="location">{currentLocation}</span>
				<span class="percent">{Math.round(currentFraction * 100)}%</span>
			</div>
		</div>

		<button class="nav-button" onclick={() => view?.goRight()} aria-label="Next page">
			<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M9 6l6 6-6 6" />
			</svg>
		</button>
	</footer>
</div>

<style>
	.reader-wrapper {
		display: flex;
		flex-direction: column;
		height: 100vh;
		height: 100dvh;
		background: var(--bg, white);
		color: var(--text, black);
	}

	@media (prefers-color-scheme: dark) {
		.reader-wrapper {
			--bg: #1a1a1a;
			--text: #e5e5e5;
			--toolbar-bg: #2a2a2a;
			--border: #404040;
		}
	}

	@media (prefers-color-scheme: light) {
		.reader-wrapper {
			--bg: white;
			--text: black;
			--toolbar-bg: #f5f5f5;
			--border: #e0e0e0;
		}
	}

	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 48px;
		padding: 0 8px;
		background: var(--toolbar-bg, #f5f5f5);
		border-bottom: 1px solid var(--border, #e0e0e0);
		flex-shrink: 0;
	}

	.toolbar-left,
	.toolbar-right {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.toolbar-center {
		flex: 1;
		text-align: center;
		overflow: hidden;
	}

	.book-title {
		font-size: 14px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.icon-button,
	.back-link {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border: none;
		background: none;
		color: inherit;
		border-radius: 8px;
		cursor: pointer;
		transition: background 0.2s;
	}

	.icon-button:hover,
	.back-link:hover {
		background: rgba(0, 0, 0, 0.1);
	}

	@media (prefers-color-scheme: dark) {
		.icon-button:hover,
		.back-link:hover {
			background: rgba(255, 255, 255, 0.1);
		}
	}

	.icon {
		display: block;
	}

	/* Sidebar */
	.sidebar-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.3);
		z-index: 10;
	}

	.sidebar {
		position: fixed;
		top: 0;
		left: 0;
		bottom: 0;
		width: 300px;
		max-width: 85vw;
		background: var(--bg, white);
		border-right: 1px solid var(--border, #e0e0e0);
		transform: translateX(-100%);
		transition: transform 0.3s ease;
		z-index: 20;
		display: flex;
		flex-direction: column;
	}

	.sidebar.open {
		transform: translateX(0);
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border, #e0e0e0);
	}

	.sidebar-header h2 {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
	}

	.toc {
		flex: 1;
		overflow-y: auto;
		padding: 8px;
	}

	.toc ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.toc-subitems {
		padding-left: 16px;
	}

	.toc-item {
		display: block;
		width: 100%;
		padding: 10px 12px;
		border: none;
		background: none;
		color: inherit;
		text-align: left;
		font-size: 14px;
		border-radius: 6px;
		cursor: pointer;
		transition: background 0.2s;
	}

	.toc-item:hover {
		background: rgba(0, 0, 0, 0.05);
	}

	@media (prefers-color-scheme: dark) {
		.toc-item:hover {
			background: rgba(255, 255, 255, 0.1);
		}
	}

	.toc-empty {
		padding: 16px;
		text-align: center;
		color: gray;
	}

	/* Main reader */
	.reader-main {
		flex: 1;
		position: relative;
		overflow: hidden;
	}

	.reader-container {
		width: 100%;
		height: 100%;
	}

	.reader-container.hidden {
		visibility: hidden;
	}

	.loading,
	.error {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 16px;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid var(--border, #e0e0e0);
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.btn {
		display: inline-block;
		padding: 8px 16px;
		background: #3b82f6;
		color: white;
		text-decoration: none;
		border-radius: 6px;
	}

	/* Navigation bar */
	.nav-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px;
		background: var(--toolbar-bg, #f5f5f5);
		border-top: 1px solid var(--border, #e0e0e0);
		flex-shrink: 0;
	}

	.nav-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border: none;
		background: none;
		color: inherit;
		border-radius: 8px;
		cursor: pointer;
		transition: background 0.2s;
	}

	.nav-button:hover {
		background: rgba(0, 0, 0, 0.1);
	}

	@media (prefers-color-scheme: dark) {
		.nav-button:hover {
			background: rgba(255, 255, 255, 0.1);
		}
	}

	.progress-container {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.progress-slider {
		width: 100%;
		height: 4px;
		-webkit-appearance: none;
		appearance: none;
		background: var(--border, #e0e0e0);
		border-radius: 2px;
		cursor: pointer;
	}

	.progress-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 16px;
		height: 16px;
		background: #3b82f6;
		border-radius: 50%;
		cursor: pointer;
	}

	.progress-slider::-moz-range-thumb {
		width: 16px;
		height: 16px;
		background: #3b82f6;
		border: none;
		border-radius: 50%;
		cursor: pointer;
	}

	.progress-info {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		color: gray;
	}

	.location {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.percent {
		margin-left: 8px;
	}
</style>
