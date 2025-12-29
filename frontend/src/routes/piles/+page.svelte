<script lang="ts">
	import { createPile, deletePile, type PileSummary } from '$lib/api';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: {
			piles: PileSummary[];
		};
	}

	let { data }: Props = $props();

	let showCreateModal = $state(false);
	let newPileName = $state('');
	let newPileDescription = $state('');
	let isCreating = $state(false);

	async function handleCreatePile() {
		if (!newPileName.trim()) return;

		isCreating = true;
		try {
			await createPile(newPileName.trim(), newPileDescription.trim() || undefined);
			newPileName = '';
			newPileDescription = '';
			showCreateModal = false;
			await invalidateAll();
		} catch (err) {
			console.error('Failed to create pile:', err);
		} finally {
			isCreating = false;
		}
	}

	async function handleDeletePile(pile: PileSummary) {
		if (pile.is_system) {
			return; // Cannot delete system piles
		}

		if (!confirm(`Are you sure you want to delete "${pile.name}"? This cannot be undone.`)) {
			return;
		}

		try {
			await deletePile(pile.id);
			await invalidateAll();
		} catch (err) {
			console.error('Failed to delete pile:', err);
		}
	}

	// Icons for system piles
	const systemPileIcons: Record<string, string> = {
		to_read: '📚',
		currently_reading: '📖',
		read: '✓'
	};
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<div class="flex justify-between items-center mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Piles</h1>
		<button
			onclick={() => (showCreateModal = true)}
			class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
		>
			New Pile
		</button>
	</div>

	{#if data.piles.length === 0}
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
					d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
				/>
			</svg>
			<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No piles</h3>
			<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
				Create a pile to organise your books.
			</p>
			<div class="mt-6">
				<button
					onclick={() => (showCreateModal = true)}
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
				>
					Create your first pile
				</button>
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each data.piles as pile (pile.id)}
				<a
					href="/piles/{pile.id}"
					class="group block bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden"
				>
					<div class="aspect-[3/2] bg-gray-200 dark:bg-gray-700 relative">
						{#if pile.first_cover_url}
							<img
								src={pile.first_cover_url}
								alt=""
								class="w-full h-full object-cover"
							/>
						{:else}
							<div class="w-full h-full flex items-center justify-center">
								<svg
									class="w-16 h-16 text-gray-400 dark:text-gray-500"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
									/>
								</svg>
							</div>
						{/if}
						<div
							class="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded"
						>
							{pile.item_count} {pile.item_count === 1 ? 'book' : 'books'}
						</div>
					</div>
					<div class="p-4">
						<div class="flex justify-between items-start">
							<div>
								<h2 class="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 flex items-center gap-2">
									{#if pile.is_system && pile.system_key}
										<span class="text-lg">{systemPileIcons[pile.system_key] || ''}</span>
									{/if}
									{pile.name}
								</h2>
								{#if pile.description}
									<p class="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
										{pile.description}
									</p>
								{/if}
							</div>
							{#if !pile.is_system}
								<button
									onclick={(e) => {
										e.preventDefault();
										e.stopPropagation();
										handleDeletePile(pile);
									}}
									class="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
									title="Delete pile"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
										/>
									</svg>
								</button>
							{/if}
						</div>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<!-- Create Pile Modal -->
{#if showCreateModal}
	<div class="fixed inset-0 z-50 overflow-y-auto">
		<div class="flex min-h-full items-center justify-center p-4">
			<!-- Backdrop -->
			<div
				class="fixed inset-0 bg-black/50 transition-opacity"
				onclick={() => (showCreateModal = false)}
			></div>

			<!-- Modal -->
			<div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Create New Pile</h2>

				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleCreatePile();
					}}
				>
					<div class="space-y-4">
						<div>
							<label
								for="pile-name"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								Name
							</label>
							<input
								id="pile-name"
								type="text"
								bind:value={newPileName}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="e.g., To Read, Favourites"
								required
							/>
						</div>

						<div>
							<label
								for="pile-description"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								Description (optional)
							</label>
							<textarea
								id="pile-description"
								bind:value={newPileDescription}
								rows="2"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="What's this pile for?"
							></textarea>
						</div>
					</div>

					<div class="flex justify-end gap-3 mt-6">
						<button
							type="button"
							onclick={() => (showCreateModal = false)}
							class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
						>
							Cancel
						</button>
						<button
							type="submit"
							disabled={isCreating || !newPileName.trim()}
							class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
						>
							{isCreating ? 'Creating...' : 'Create'}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
{/if}
