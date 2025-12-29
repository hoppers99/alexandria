<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { login } from '$lib/api';

	// Get redirect URL from query params
	const redirectTo = $page.url.searchParams.get('redirect') || '/';

	let username = $state('');
	let password = $state('');
	let rememberMe = $state(false);
	let error = $state<string | null>(null);
	let isLoading = $state(false);

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;
		isLoading = true;

		try {
			const result = await login(username, password, rememberMe);
			console.log('Login successful:', result);

			// Check if cookie was set
			console.log('All cookies:', document.cookie);

			// Wait a moment then redirect
			setTimeout(() => {
				window.location.href = redirectTo;
			}, 100);
		} catch (err) {
			console.error('Login failed:', err);
			error = err instanceof Error ? err.message : 'Login failed';
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Login - Alexandria</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-4">
	<div class="max-w-md w-full">
		<!-- Logo and Title -->
		<div class="text-center mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white">Alexandria</h1>
			<p class="mt-2 text-gray-600 dark:text-gray-400">Sign in to your library</p>
		</div>

		<!-- Login Form -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
			<form onsubmit={handleSubmit}>
				{#if error}
					<div class="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
						{error}
					</div>
				{/if}

				<div class="mb-4">
					<label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Username
					</label>
					<input
						type="text"
						id="username"
						bind:value={username}
						required
						autofocus
						disabled={isLoading}
						class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
						placeholder="Enter your username"
					/>
				</div>

				<div class="mb-4">
					<label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Password
					</label>
					<input
						type="password"
						id="password"
						bind:value={password}
						required
						disabled={isLoading}
						class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
						placeholder="Enter your password"
					/>
				</div>

				<div class="mb-6 flex items-center">
					<input
						type="checkbox"
						id="remember"
						bind:checked={rememberMe}
						disabled={isLoading}
						class="w-4 h-4 text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
					/>
					<label for="remember" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
						Remember me for 30 days
					</label>
				</div>

				<button
					type="submit"
					disabled={isLoading || !username || !password}
					class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
				>
					{isLoading ? 'Signing in...' : 'Sign in'}
				</button>
			</form>
		</div>

		<p class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
			Your personal digital library
		</p>
	</div>
</div>
