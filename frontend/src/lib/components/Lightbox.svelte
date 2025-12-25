<script lang="ts">
	interface Props {
		imageUrl: string | null;
		title?: string;
		onClose: () => void;
	}

	let { imageUrl, title = '', onClose }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

{#if imageUrl}
	<div
		class="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
		onclick={onClose}
		onkeydown={handleKeydown}
		role="dialog"
		aria-modal="true"
		aria-label={title}
		tabindex="-1"
	>
		<div class="relative max-w-3xl max-h-[90vh]">
			<!-- Close button -->
			<button
				onclick={onClose}
				class="absolute -top-10 right-0 text-white hover:text-gray-300 p-2"
				aria-label="Close"
			>
				<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>

			<!-- Title -->
			{#if title}
				<div class="absolute -top-10 left-0 text-white text-lg font-medium">
					{title}
				</div>
			{/if}

			<!-- Image - wrapped in button to handle click without propagating -->
			<button
				type="button"
				onclick={(e) => e.stopPropagation()}
				class="cursor-default focus:outline-none"
			>
				<img
					src={imageUrl}
					alt={title}
					class="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
				/>
			</button>
		</div>
	</div>
{/if}
