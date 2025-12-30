<script lang="ts">
	import { changePassword, getTTSSettings, updateTTSSettings, getAvailableVoices, getTTSAvailability, type TTSSettings, type AvailableVoicesResponse, type EngineStatus } from '$lib/api';
	import { onMount } from 'svelte';

	let { data } = $props();

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);
	let isLoading = $state(false);

	// TTS Settings (admin only)
	let ttsSettings = $state<TTSSettings | null>(null);
	let availableVoices = $state<AvailableVoicesResponse | null>(null);
	let engineAvailability = $state<EngineStatus[]>([]);
	let ttsError = $state<string | null>(null);
	let ttsSuccess = $state<string | null>(null);
	let ttsLoading = $state(false);
	let checkingAvailability = $state(false);

	async function handleChangePassword(event: Event) {
		event.preventDefault();
		error = null;
		success = null;

		// Validate passwords match
		if (newPassword !== confirmPassword) {
			error = 'New passwords do not match';
			return;
		}

		// Validate password length
		if (newPassword.length < 12) {
			error = 'Password must be at least 12 characters long';
			return;
		}

		isLoading = true;

		try {
			await changePassword(currentPassword, newPassword);
			success = 'Password changed successfully';
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
		} catch (err) {
			console.error('Password change failed:', err);
			error = err instanceof Error ? err.message : 'Failed to change password';
		} finally {
			isLoading = false;
		}
	}

	// TTS Settings functions
	async function loadTTSSettings() {
		if (!data.user.is_admin) return;

		try {
			// Load settings and availability in parallel
			checkingAvailability = true;
			const [settings, availability] = await Promise.all([
				getTTSSettings(),
				getTTSAvailability()
			]);

			ttsSettings = settings;
			engineAvailability = availability.engines;
			checkingAvailability = false;

			await loadVoices(ttsSettings.engine);
		} catch (err) {
			console.error('Failed to load TTS settings:', err);
			ttsError = err instanceof Error ? err.message : 'Failed to load TTS settings';
			checkingAvailability = false;
		}
	}

	async function loadVoices(engine: 'coqui' | 'chatterbox') {
		try {
			availableVoices = await getAvailableVoices(engine);
		} catch (err) {
			console.error('Failed to load voices:', err);
		}
	}

	function isEngineAvailable(engine: 'coqui' | 'chatterbox'): boolean {
		const status = engineAvailability.find(e => e.engine === engine);
		return status?.available ?? false;
	}

	function getEngineError(engine: 'coqui' | 'chatterbox'): string | undefined {
		const status = engineAvailability.find(e => e.engine === engine);
		return status?.error;
	}

	async function handleEngineChange(engine: 'coqui' | 'chatterbox') {
		if (!ttsSettings) return;

		ttsError = null;
		ttsSuccess = null;
		ttsLoading = true;

		try {
			ttsSettings = await updateTTSSettings({ engine });
			await loadVoices(engine);
			ttsSuccess = 'TTS engine updated successfully';
		} catch (err) {
			console.error('Failed to update engine:', err);
			ttsError = err instanceof Error ? err.message : 'Failed to update engine';
		} finally {
			ttsLoading = false;
		}
	}

	async function handleVoiceChange(voice: string) {
		if (!ttsSettings) return;

		ttsError = null;
		ttsSuccess = null;
		ttsLoading = true;

		try {
			ttsSettings = await updateTTSSettings({ voice });
			ttsSuccess = 'Voice updated successfully';
		} catch (err) {
			console.error('Failed to update voice:', err);
			ttsError = err instanceof Error ? err.message : 'Failed to update voice';
		} finally {
			ttsLoading = false;
		}
	}

	async function handleExaggerationChange(exaggeration: number) {
		if (!ttsSettings) return;

		ttsError = null;
		ttsSuccess = null;

		try {
			ttsSettings = await updateTTSSettings({ exaggeration });
		} catch (err) {
			console.error('Failed to update exaggeration:', err);
			ttsError = err instanceof Error ? err.message : 'Failed to update emotion intensity';
		}
	}

	onMount(() => {
		if (data.user.is_admin) {
			loadTTSSettings();
		}
	});
</script>

<svelte:head>
	<title>Settings - Alexandria</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-8">
	<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-8">Settings</h1>

	<!-- User Information -->
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Account Information</h2>

		<div class="space-y-3">
			<div>
				<label class="text-sm font-medium text-gray-500 dark:text-gray-400">Username</label>
				<p class="text-gray-900 dark:text-white">{data.user.username}</p>
			</div>

			{#if data.user.email}
				<div>
					<label class="text-sm font-medium text-gray-500 dark:text-gray-400">Email</label>
					<p class="text-gray-900 dark:text-white">{data.user.email}</p>
				</div>
			{/if}

			<div>
				<label class="text-sm font-medium text-gray-500 dark:text-gray-400">Role</label>
				<p class="text-gray-900 dark:text-white">
					{data.user.is_admin ? 'Administrator' : 'User'}
					{#if !data.user.can_download}
						<span class="ml-2 text-sm text-yellow-600 dark:text-yellow-400">
							(Downloads disabled)
						</span>
					{/if}
				</p>
			</div>

			<div>
				<label class="text-sm font-medium text-gray-500 dark:text-gray-400">Member Since</label>
				<p class="text-gray-900 dark:text-white">
					{new Date(data.user.created_at).toLocaleDateString()}
				</p>
			</div>
		</div>
	</div>

	<!-- Change Password -->
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Change Password</h2>

		<form onsubmit={handleChangePassword} class="space-y-4">
			{#if error}
				<div class="p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
					{error}
				</div>
			{/if}

			{#if success}
				<div class="p-3 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg text-sm">
					{success}
				</div>
			{/if}

			<div>
				<label for="current-password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					Current Password
				</label>
				<input
					type="password"
					id="current-password"
					bind:value={currentPassword}
					required
					disabled={isLoading}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
					placeholder="Enter your current password"
				/>
			</div>

			<div>
				<label for="new-password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					New Password
				</label>
				<input
					type="password"
					id="new-password"
					bind:value={newPassword}
					required
					disabled={isLoading}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
					placeholder="Enter your new password"
				/>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					Must be at least 12 characters with uppercase, lowercase, number, and special character
				</p>
			</div>

			<div>
				<label for="confirm-password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					Confirm New Password
				</label>
				<input
					type="password"
					id="confirm-password"
					bind:value={confirmPassword}
					required
					disabled={isLoading}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
					placeholder="Confirm your new password"
				/>
			</div>

			<div class="pt-2">
				<button
					type="submit"
					disabled={isLoading || !currentPassword || !newPassword || !confirmPassword}
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
				>
					{isLoading ? 'Changing Password...' : 'Change Password'}
				</button>
			</div>
		</form>
	</div>

	<!-- TTS Settings (Admin Only) -->
	{#if data.user.is_admin}
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mt-6">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Text-to-Speech Settings</h2>
			<p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
				Configure system-wide TTS engine and voice for audiobook narration
			</p>

			{#if ttsError}
				<div class="p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm mb-4">
					{ttsError}
				</div>
			{/if}

			{#if ttsSuccess}
				<div class="p-3 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg text-sm mb-4">
					{ttsSuccess}
				</div>
			{/if}

			{#if ttsSettings}
				<div class="space-y-6">
					<!-- Engine Selection -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							TTS Engine
						</label>
						<div class="grid grid-cols-2 gap-3">
							<button
								type="button"
								onclick={() => handleEngineChange('chatterbox')}
								disabled={ttsLoading || checkingAvailability || !isEngineAvailable('chatterbox')}
								class="px-4 py-3 rounded-lg border-2 transition-all text-left {ttsSettings.engine === 'chatterbox'
									? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
									: 'border-gray-300 dark:border-gray-600'} disabled:opacity-50 disabled:cursor-not-allowed"
							>
								<div class="flex items-center gap-2">
									<div class="font-medium text-gray-900 dark:text-white">Chatterbox</div>
									{#if checkingAvailability}
										<span class="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></span>
									{:else if isEngineAvailable('chatterbox')}
										<span class="w-2 h-2 rounded-full bg-green-500"></span>
									{:else}
										<span class="w-2 h-2 rounded-full bg-red-500"></span>
									{/if}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{#if !checkingAvailability && !isEngineAvailable('chatterbox')}
										{getEngineError('chatterbox') || 'Unavailable'}
									{:else}
										Emotion control, best quality
									{/if}
								</div>
							</button>
							<button
								type="button"
								onclick={() => handleEngineChange('coqui')}
								disabled={ttsLoading || checkingAvailability || !isEngineAvailable('coqui')}
								class="px-4 py-3 rounded-lg border-2 transition-all text-left {ttsSettings.engine === 'coqui'
									? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
									: 'border-gray-300 dark:border-gray-600'} disabled:opacity-50 disabled:cursor-not-allowed"
							>
								<div class="flex items-center gap-2">
									<div class="font-medium text-gray-900 dark:text-white">Coqui VCTK</div>
									{#if checkingAvailability}
										<span class="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></span>
									{:else if isEngineAvailable('coqui')}
										<span class="w-2 h-2 rounded-full bg-green-500"></span>
									{:else}
										<span class="w-2 h-2 rounded-full bg-red-500"></span>
									{/if}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{#if !checkingAvailability && !isEngineAvailable('coqui')}
										{getEngineError('coqui') || 'Unavailable'}
									{:else}
										Multi-accent, lightweight
									{/if}
								</div>
							</button>
						</div>
					</div>

					<!-- Voice Selection -->
					{#if availableVoices}
						<div>
							<label for="voice-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Voice
							</label>
							<select
								id="voice-select"
								bind:value={ttsSettings.voice}
								onchange={(e) => handleVoiceChange((e.target as HTMLSelectElement).value)}
								disabled={ttsLoading}
								class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
							>
								{#each availableVoices.voices as voice}
									<option value={voice.voice_id}>
										{voice.description}
										{#if voice.gender}({voice.gender}){/if}
									</option>
								{/each}
							</select>
						</div>
					{/if}

					<!-- Emotion Intensity (Chatterbox only) -->
					{#if ttsSettings.engine === 'chatterbox'}
						<div>
							<label for="exaggeration-slider" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Emotion Intensity: {ttsSettings.exaggeration.toFixed(2)}
							</label>
							<div class="flex items-center gap-3">
								<span class="text-xs text-gray-500 dark:text-gray-400 w-12">Calm</span>
								<input
									id="exaggeration-slider"
									type="range"
									min="0.25"
									max="2.0"
									step="0.05"
									bind:value={ttsSettings.exaggeration}
									onchange={(e) => handleExaggerationChange(parseFloat((e.target as HTMLInputElement).value))}
									disabled={ttsLoading}
									class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
								/>
								<span class="text-xs text-gray-500 dark:text-gray-400 w-16">Dramatic</span>
							</div>
							<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
								{#if ttsSettings.exaggeration < 0.5}
									Very neutral, professional narration
								{:else if ttsSettings.exaggeration < 0.8}
									Balanced, natural expression
								{:else if ttsSettings.exaggeration < 1.2}
									Expressive, engaging narration
								{:else}
									Very dramatic, theatrical style
								{/if}
							</p>
						</div>
					{/if}

					<!-- Info Box -->
					<div class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
						<div class="flex gap-3">
							<div class="text-blue-600 dark:text-blue-400">
								<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
								</svg>
							</div>
							<div class="text-sm text-blue-800 dark:text-blue-300">
								<strong>Note:</strong> These settings apply system-wide to all TTS audiobook generation.
								Changes take effect for new audiobook chapters.
							</div>
						</div>
					</div>
				</div>
			{:else}
				<div class="text-center py-8 text-gray-500 dark:text-gray-400">
					Loading TTS settings...
				</div>
			{/if}
		</div>
	{/if}
</div>
