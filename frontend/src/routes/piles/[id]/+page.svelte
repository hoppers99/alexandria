<script lang="ts">
	import BookCard from '$lib/components/BookCard.svelte';
	import { removeItemsFromPile, updatePile, type PileDetail } from '$lib/api';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: {
			pile: PileDetail;
		};
	}

	let { data }: Props = $props();

	let isEditing = $state(false);
	let editName = $state(data.pile.name);
	let editDescription = $state(data.pile.description || '');
	let isSaving = $state(false);
	let selectedItems = $state<Set<number>>(new Set());
	let isSelectionMode = $state(false);

	function toggleSelection(itemId: number) {
		const newSet = new Set(selectedItems);
		if (newSet.has(itemId)) {
			newSet.delete(itemId);
		} else {
			newSet.add(itemId);
		}
		selectedItems = newSet;
	}

	function selectAll() {
		selectedItems = new Set(data.pile.items.map((i) => i.id));
	}

	function clearSelection() {
		selectedItems = new Set();
		isSelectionMode = false;
	}

	async function removeSelected() {
		if (selectedItems.size === 0) return;

		if (
			!confirm(
				`Remove ${selectedItems.size} ${selectedItems.size === 1 ? 'book' : 'books'} from this pile?`
			)
		) {
			return;
		}

		try {
			await removeItemsFromPile(data.pile.id, Array.from(selectedItems));
			selectedItems = new Set();
			isSelectionMode = false;
			await invalidateAll();
		} catch (err) {
			console.error('Failed to remove items:', err);
		}
	}

	async function saveEdit() {
		if (!editName.trim()) return;

		isSaving = true;
		try {
			await updatePile(data.pile.id, {
				name: editName.trim(),
				description: editDescription.trim() || undefined
			});
			isEditing = false;
			await invalidateAll();
		} catch (err) {
			console.error('Failed to update pile:', err);
		} finally {
			isSaving = false;
		}
	}

	function startEdit() {
		editName = data.pile.name;
		editDescription = data.pile.description || '';
		isEditing = true;
	}
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header -->
	<div class="mb-6">
		<a
			href="/piles"
			class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 mb-2 inline-block"
		>
			&larr; Back to Piles
		</a>

		{#if isEditing}
			<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
				<div class="space-y-4">
					<div>
						<label
							for="edit-name"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							Name
						</label>
						<input
							id="edit-name"
							type="text"
							bind:value={editName}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						/>
					</div>
					<div>
						<label
							for="edit-description"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							Description
						</label>
						<textarea
							id="edit-description"
							bind:value={editDescription}
							rows="2"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						></textarea>
					</div>
					<div class="flex gap-2">
						<button
							onclick={saveEdit}
							disabled={isSaving || !editName.trim()}
							class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
						>
							{isSaving ? 'Saving...' : 'Save'}
						</button>
						<button
							onclick={() => (isEditing = false)}
							class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
						>
							Cancel
						</button>
					</div>
				</div>
			</div>
		{:else}
			<div class="flex justify-between items-start">
				<div>
					<h1 class="text-2xl font-bold text-gray-900 dark:text-white">{data.pile.name}</h1>
					{#if data.pile.description}
						<p class="text-gray-500 dark:text-gray-400 mt-1">{data.pile.description}</p>
					{/if}
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
						{data.pile.items.length}
						{data.pile.items.length === 1 ? 'book' : 'books'}
					</p>
				</div>
				<div class="flex gap-2">
					<button
						onclick={startEdit}
						class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
						title="Edit pile"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
							/>
						</svg>
					</button>
					{#if data.pile.items.length > 0}
						<button
							onclick={() => (isSelectionMode = !isSelectionMode)}
							class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 {isSelectionMode
								? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400'
								: ''}"
							title={isSelectionMode ? 'Exit selection mode' : 'Select items'}
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- Selection toolbar -->
	{#if isSelectionMode}
		<div
			class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4 flex justify-between items-center"
		>
			<span class="text-sm text-blue-800 dark:text-blue-200">
				{selectedItems.size} selected
			</span>
			<div class="flex gap-2">
				<button
					onclick={selectAll}
					class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
				>
					Select all
				</button>
				<button
					onclick={clearSelection}
					class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
				>
					Clear
				</button>
				{#if selectedItems.size > 0}
					<button
						onclick={removeSelected}
						class="text-sm text-red-600 dark:text-red-400 hover:underline"
					>
						Remove from pile
					</button>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Books grid -->
	{#if data.pile.items.length === 0}
		<div class="text-center py-12">
			<svg
				class="mx-auto h-12 w-12 text-gray-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
				/>
			</svg>
			<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No books in this pile</h3>
			<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
				Add books from the library to this pile.
			</p>
			<div class="mt-6">
				<a
					href="/browse"
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-block"
				>
					Browse library
				</a>
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
			{#each data.pile.items as item (item.id)}
				{#if isSelectionMode}
					<div
						class="relative cursor-pointer"
						onclick={() => toggleSelection(item.id)}
						onkeydown={(e) => e.key === 'Enter' && toggleSelection(item.id)}
						role="checkbox"
						aria-checked={selectedItems.has(item.id)}
						tabindex="0"
					>
						<div
							class="absolute inset-0 z-10 {selectedItems.has(item.id)
								? 'bg-blue-500/20 ring-2 ring-blue-500 rounded-lg'
								: ''}"
						></div>
						<div
							class="absolute top-2 left-2 z-20 w-5 h-5 rounded border-2 flex items-center justify-center {selectedItems.has(
								item.id
							)
								? 'bg-blue-600 border-blue-600'
								: 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600'}"
						>
							{#if selectedItems.has(item.id)}
								<svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</div>
						<BookCard {item} />
					</div>
				{:else}
					<BookCard {item} />
				{/if}
			{/each}
		</div>
	{/if}
</div>
