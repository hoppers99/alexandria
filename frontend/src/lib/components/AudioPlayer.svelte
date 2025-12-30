<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		getItemChapters,
		generateChapterAudio,
		getChapterAudioUrl,
		type ChapterInfo
	} from '$lib/api';
	import { formatDuration } from '$lib/format';

	interface Props {
		itemId: number;
		itemTitle: string;
		coverUrl?: string | null;
	}

	let { itemId, itemTitle, coverUrl }: Props = $props();

	let audioElement: HTMLAudioElement;
	let chapters: ChapterInfo[] = $state([]);
	let currentChapter: number | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	// Playback state
	let playing = $state(false);
	let currentTime = $state(0);
	let duration = $state(0);
	let volume = $state(1);
	let playbackRate = $state(1.0);

	// Generation state
	let generatingAll = $state(false);
	let generatingChapter: number | null = $state(null);
	let generationQueue: number[] = $state([]);

	$effect(() => {
		// Update audio source when chapter changes
		if (audioElement && currentChapter !== null && currentChapterHasAudio) {
			// Use system default voice (no voice_id parameter)
			const url = getChapterAudioUrl(itemId, currentChapter);
			audioElement.src = url;
			audioElement.load();
			audioElement.playbackRate = playbackRate; // Maintain playback speed
		}
	});

	const currentChapterData = $derived(
		currentChapter !== null ? chapters.find((ch) => ch.number === currentChapter) : null
	);

	const currentChapterHasAudio = $derived(currentChapterData?.has_audio ?? false);

	const hasAnyAudio = $derived(chapters.some((ch) => ch.has_audio));

	const totalDuration = $derived(
		chapters
			.filter((ch) => ch.has_audio)
			.reduce((sum, ch) => sum + (ch.audio_duration_seconds || 0), 0)
	);

	async function loadData() {
		try {
			loading = true;
			error = null;

			// Load chapters (API uses system default voice)
			const chaptersData = await getItemChapters(itemId);
			chapters = chaptersData.chapters;

			// Start with first chapter that has audio, or first chapter
			const firstWithAudio = chapters.find((ch) => ch.has_audio);
			currentChapter = firstWithAudio?.number ?? (chapters.length > 0 ? chapters[0].number : null);

			loading = false;
		} catch (e: any) {
			error = e.message;
			loading = false;
		}
	}

	async function generateAllChapters() {
		generatingAll = true;
		generationQueue = chapters
			.filter((ch) => !ch.has_audio)
			.map((ch) => ch.number);

		for (const chapterNum of generationQueue) {
			try {
				generatingChapter = chapterNum;
				// Generate using system default voice (no voice parameter)
				await generateChapterAudio(itemId, chapterNum);

				// Reload chapter data
				const chaptersData = await getItemChapters(itemId);
				chapters = chaptersData.chapters;

				// Remove from queue
				generationQueue = generationQueue.filter((n) => n !== chapterNum);
			} catch (e: any) {
				console.error(`Failed to generate chapter ${chapterNum}:`, e);
				error = `Failed to generate chapter ${chapterNum}: ${e.message}`;
				break;
			}
		}

		generatingChapter = null;
		generatingAll = false;
		generationQueue = [];
	}

	function playChapter(chapterNumber: number) {
		const chapter = chapters.find((ch) => ch.number === chapterNumber);
		if (!chapter || !chapter.has_audio) {
			return;
		}

		currentChapter = chapterNumber;
		if (audioElement) {
			audioElement.play();
		}
	}

	function togglePlay() {
		if (!audioElement || currentChapter === null || !currentChapterHasAudio) return;

		if (playing) {
			audioElement.pause();
		} else {
			audioElement.play();
		}
	}

	function seek(event: Event) {
		if (!audioElement) return;
		const target = event.target as HTMLInputElement;
		audioElement.currentTime = parseFloat(target.value);
	}

	function changeVolume(event: Event) {
		if (!audioElement) return;
		const target = event.target as HTMLInputElement;
		volume = parseFloat(target.value);
		audioElement.volume = volume;
	}

	function changePlaybackRate(rate: number) {
		playbackRate = rate;
		if (audioElement) {
			audioElement.playbackRate = rate;
		}
		// Save preference to localStorage
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('audioPlaybackRate', rate.toString());
		}
	}

	function nextChapter() {
		if (currentChapter === null) return;
		const nextCh = chapters.find((ch) => ch.number > currentChapter! && ch.has_audio);
		if (nextCh) {
			playChapter(nextCh.number);
		}
	}

	function previousChapter() {
		if (currentChapter === null) return;
		const prevCh = [...chapters]
			.reverse()
			.find((ch) => ch.number < currentChapter! && ch.has_audio);
		if (prevCh) {
			playChapter(prevCh.number);
		}
	}

	onMount(() => {
		// Restore saved playback rate
		if (typeof localStorage !== 'undefined') {
			const savedRate = localStorage.getItem('audioPlaybackRate');
			if (savedRate) {
				playbackRate = parseFloat(savedRate);
			}
		}

		loadData();

		if (audioElement) {
			audioElement.playbackRate = playbackRate;
			audioElement.addEventListener('play', () => (playing = true));
			audioElement.addEventListener('pause', () => (playing = false));
			audioElement.addEventListener('timeupdate', () => {
				currentTime = audioElement.currentTime;
				duration = audioElement.duration || 0;
			});
			audioElement.addEventListener('ended', () => {
				nextChapter();
			});
		}
	});

	onDestroy(() => {
		if (audioElement) {
			audioElement.pause();
		}
	});
</script>

<div class="player-container">
	<audio bind:this={audioElement} preload="metadata"></audio>

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
			<p>Loading audio data...</p>
		</div>
	{:else if error}
		<div class="error">{error}</div>
	{:else}
		<!-- Header with Album Art & Info -->
		<div class="player-header">
			<div class="album-art-compact">
				{#if coverUrl}
					<img src={coverUrl} alt={itemTitle} />
				{:else}
					<div class="placeholder-art">
						<svg width="32" height="32" fill="currentColor" viewBox="0 0 24 24">
							<path
								d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"
							/>
						</svg>
					</div>
				{/if}
			</div>
			<div class="header-info">
				<h2 class="book-title">{itemTitle}</h2>
				<div class="meta-row">
					<span class="chapter-count">{chapters.length} chapters</span>
					{#if totalDuration > 0}
						<span class="total-duration">• {formatDuration(totalDuration)}</span>
					{/if}
				</div>
			</div>
		</div>

		<!-- Player Controls (when audio exists) -->
		{#if hasAnyAudio && currentChapter !== null}
			<div class="player-controls">
				<div class="controls-row">
					<button class="control-btn-compact" onclick={previousChapter}>
						<svg width="18" height="18" fill="currentColor">
							<path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
						</svg>
					</button>

					<button class="control-btn-compact play-pause" onclick={togglePlay}>
						{#if playing}
							<svg width="24" height="24" fill="currentColor">
								<path d="M6 4h4v16H6zM14 4h4v16h-4z" />
							</svg>
						{:else}
							<svg width="24" height="24" fill="currentColor">
								<path d="M8 5v14l11-7z" />
							</svg>
						{/if}
					</button>

					<button class="control-btn-compact" onclick={nextChapter}>
						<svg width="18" height="18" fill="currentColor">
							<path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
						</svg>
					</button>

					<div class="playback-controls-right">
						<button class="speed-btn" onclick={() => {
							const speeds = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0];
							const currentIndex = speeds.indexOf(playbackRate);
							const nextIndex = (currentIndex + 1) % speeds.length;
							changePlaybackRate(speeds[nextIndex]);
						}}>
							{playbackRate}x
						</button>
						<div class="time-compact">
							{formatDuration(currentTime)} / {formatDuration(duration)}
						</div>
					</div>
				</div>

				<input
					type="range"
					class="progress-bar-compact"
					min="0"
					max={duration || 0}
					value={currentTime}
					oninput={seek}
				/>
			</div>
		{/if}

		<!-- Generate All Button (when no audio) -->
		{#if !hasAnyAudio && !generatingAll}
			<div class="generate-section-compact">
				<button class="generate-all-btn" onclick={generateAllChapters}>
					<svg width="16" height="16" fill="currentColor">
						<path
							d="M12 3v9.28c-.47-.17-.97-.28-1.5-.28C8.01 12 6 14.01 6 16.5S8.01 21 10.5 21c2.31 0 4.2-1.75 4.45-4H15V6h4V3h-7z"
						/>
					</svg>
					Generate All Chapters
				</button>
			</div>
		{/if}

		<!-- Generation Progress -->
		{#if generatingAll}
			<div class="generation-progress-compact">
				<div class="progress-text">
					Generating... {generationQueue.length} remaining
				</div>
				<div class="progress-bar-container">
					<div
						class="progress-fill"
						style="width: {((chapters.length - generationQueue.length) / chapters.length) * 100}%"
					></div>
				</div>
			</div>
		{/if}

		<!-- Chapter List -->
		<div class="chapter-list-compact">
			{#each chapters as chapter}
				<button
					class="chapter-row-compact"
					class:active={currentChapter === chapter.number}
					class:has-audio={chapter.has_audio}
					class:generating={generatingChapter === chapter.number}
					class:disabled={!chapter.has_audio}
					onclick={() => playChapter(chapter.number)}
					disabled={!chapter.has_audio}
				>
					<div class="chapter-num-badge">{chapter.number}</div>
					<div class="chapter-info">
						<div class="chapter-title-compact">
							{#if chapter.title && chapter.title !== '[ONE]'}
								{chapter.title}
							{:else}
								Chapter {chapter.number}
							{/if}
						</div>
						<div class="chapter-meta-compact">
							{#if generatingChapter === chapter.number}
								<span class="status-dot generating"></span>
								<span>Generating...</span>
							{:else if chapter.has_audio}
								<span class="status-dot ready"></span>
								<span>{formatDuration(chapter.audio_duration_seconds || 0)}</span>
							{:else}
								<span class="status-dot pending"></span>
								<span>~{formatDuration(chapter.estimated_duration_seconds)}</span>
							{/if}
						</div>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.player-container {
		width: 100%;
		max-width: 420px;
		background: rgba(15, 15, 17, 0.95);
		backdrop-filter: blur(20px);
		border-radius: 16px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
		overflow: visible; /* Changed from hidden to allow dropdown */
		position: relative;
	}

	@media (prefers-color-scheme: dark) {
		.player-container {
			background: rgba(15, 15, 17, 0.98);
		}
	}

	.loading,
	.error {
		text-align: center;
		padding: 2rem 1rem;
	}

	.spinner {
		width: 32px;
		height: 32px;
		margin: 0 auto 0.75rem;
		border: 3px solid rgba(99, 102, 241, 0.15);
		border-radius: 50%;
		border-top-color: #6366f1;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.error {
		color: #f87171;
		background: rgba(248, 113, 113, 0.1);
		padding: 0.875rem;
		margin: 0.75rem;
		border-radius: 8px;
		border: 1px solid rgba(248, 113, 113, 0.2);
		font-size: 0.875rem;
	}

	/* Header */
	.player-header {
		display: flex;
		gap: 0.875rem;
		padding: 1rem;
		background: rgba(20, 20, 24, 0.5);
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
	}

	.album-art-compact {
		width: 48px;
		height: 72px; /* Portrait aspect ratio (2:3) for book covers */
		border-radius: 6px;
		overflow: hidden;
		flex-shrink: 0;
		background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		border: 1px solid rgba(255, 255, 255, 0.08);
	}

	.album-art-compact img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.placeholder-art {
		color: rgba(255, 255, 255, 0.25);
	}

	.header-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		min-width: 0;
	}

	.book-title {
		font-size: 1.0625rem;
		font-weight: 700;
		margin: 0 0 0.375rem 0;
		color: rgba(255, 255, 255, 0.95);
		letter-spacing: -0.01em;
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.meta-row {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.5);
	}

	.chapter-count {
		color: rgba(255, 255, 255, 0.5);
	}

	.total-duration {
		color: rgba(255, 255, 255, 0.5);
	}

	/* Player Controls */
	.player-controls {
		padding: 0.875rem 1rem;
		background: rgba(20, 20, 24, 0.3);
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
	}

	.controls-row {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.control-btn-compact {
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 50%;
		transition: all 0.2s;
		color: rgba(255, 255, 255, 0.8);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.control-btn-compact:hover {
		background: rgba(255, 255, 255, 0.12);
		border-color: rgba(255, 255, 255, 0.2);
		transform: scale(1.05);
	}

	.control-btn-compact.play-pause {
		background: linear-gradient(135deg, #6366f1, #8b5cf6);
		color: white;
		padding: 0.625rem;
		border: none;
		box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
	}

	.control-btn-compact.play-pause:hover {
		background: linear-gradient(135deg, #818cf8, #a78bfa);
		box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
	}

	.playback-controls-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-left: auto;
	}

	.speed-btn {
		padding: 0.25rem 0.5rem;
		background: rgba(99, 102, 241, 0.15);
		border: 1px solid rgba(99, 102, 241, 0.25);
		border-radius: 6px;
		color: rgba(255, 255, 255, 0.9);
		font-size: 0.6875rem;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.2s;
		min-width: 42px;
		text-align: center;
	}

	.speed-btn:hover {
		background: rgba(99, 102, 241, 0.25);
		border-color: rgba(99, 102, 241, 0.4);
		transform: scale(1.05);
	}

	.time-compact {
		font-size: 0.6875rem;
		color: rgba(255, 255, 255, 0.6);
		font-variant-numeric: tabular-nums;
	}

	.progress-bar-compact {
		width: 100%;
		height: 4px;
		-webkit-appearance: none;
		appearance: none;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 2px;
		outline: none;
		cursor: pointer;
	}

	.progress-bar-compact::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: linear-gradient(135deg, #6366f1, #8b5cf6);
		cursor: pointer;
		box-shadow: 0 1px 6px rgba(99, 102, 241, 0.4);
	}

	.progress-bar-compact::-moz-range-thumb {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: linear-gradient(135deg, #6366f1, #8b5cf6);
		cursor: pointer;
		border: none;
		box-shadow: 0 1px 6px rgba(99, 102, 241, 0.4);
	}

	/* Generate Section */
	.generate-section-compact {
		padding: 1.25rem 1rem;
		text-align: center;
		background: rgba(20, 20, 24, 0.3);
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
	}

	.generate-all-btn {
		padding: 0.625rem 1.25rem;
		background: linear-gradient(135deg, #6366f1, #8b5cf6);
		color: white;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.8125rem;
		cursor: pointer;
		transition: all 0.25s ease;
		box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}

	.generate-all-btn:hover {
		background: linear-gradient(135deg, #818cf8, #a78bfa);
		box-shadow: 0 4px 16px rgba(99, 102, 241, 0.5);
		transform: translateY(-1px);
	}

	/* Generation Progress */
	.generation-progress-compact {
		padding: 0.875rem 1rem;
		background: rgba(99, 102, 241, 0.08);
		border-bottom: 1px solid rgba(99, 102, 241, 0.2);
	}

	.progress-text {
		font-size: 0.75rem;
		font-weight: 600;
		color: rgba(255, 255, 255, 0.9);
		margin-bottom: 0.5rem;
	}

	.progress-bar-container {
		height: 4px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 2px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #6366f1, #8b5cf6);
		transition: width 0.3s ease;
	}

	/* Chapter List */
	.chapter-list-compact {
		max-height: 320px;
		overflow-y: auto;
		border-radius: 0 0 16px 16px;
	}

	.chapter-row-compact {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: transparent;
		border: none;
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
		cursor: pointer;
		transition: all 0.2s;
		text-align: left;
		width: 100%;
	}

	.chapter-row-compact:last-child {
		border-bottom: none;
	}

	.chapter-row-compact.has-audio:hover {
		background: rgba(255, 255, 255, 0.04);
	}

	.chapter-row-compact.active {
		background: linear-gradient(90deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.08));
		border-left: 2px solid #6366f1;
		padding-left: calc(1rem - 2px);
	}

	.chapter-row-compact.disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.chapter-row-compact.generating {
		background: rgba(99, 102, 241, 0.06);
	}

	.chapter-num-badge {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(255, 255, 255, 0.06);
		border-radius: 6px;
		font-weight: 700;
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.6);
		flex-shrink: 0;
		border: 1px solid rgba(255, 255, 255, 0.08);
	}

	.chapter-row-compact.active .chapter-num-badge {
		background: linear-gradient(135deg, #6366f1, #8b5cf6);
		color: white;
		border-color: transparent;
		box-shadow: 0 1px 6px rgba(99, 102, 241, 0.3);
	}

	.chapter-info {
		flex: 1;
		min-width: 0;
	}

	.chapter-title-compact {
		font-weight: 600;
		font-size: 0.8125rem;
		color: rgba(255, 255, 255, 0.95);
		margin-bottom: 0.25rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		letter-spacing: -0.005em;
	}

	.chapter-meta-compact {
		font-size: 0.6875rem;
		color: rgba(255, 255, 255, 0.5);
		display: flex;
		align-items: center;
		gap: 0.375rem;
	}

	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.status-dot.ready {
		background: #34d399;
		box-shadow: 0 0 6px rgba(52, 211, 153, 0.5);
	}

	.status-dot.pending {
		background: #fbbf24;
	}

	.status-dot.generating {
		background: #818cf8;
		animation: pulse 1.5s ease-in-out infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.4;
		}
	}
</style>
