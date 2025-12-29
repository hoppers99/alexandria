<script lang="ts">
	import { changePassword } from '$lib/api';

	let { data } = $props();

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);
	let isLoading = $state(false);

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
</div>
