<script lang="ts">
	import '../app.css';
	import { logout } from '$lib/api';

	let { children, data } = $props();

	let showUserMenu = $state(false);

	async function handleLogout() {
		try {
			await logout();
			window.location.href = '/login';
		} catch (error) {
			console.error('Logout failed:', error);
			// Force redirect anyway
			window.location.href = '/login';
		}
	}
</script>

<svelte:head>
	<title>Alexandria</title>
	<meta name="description" content="Your personal digital library" />
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<!-- Top navigation -->
	<header class="sticky top-0 z-50 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
		<nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex justify-between h-16">
				<div class="flex items-center">
					<a href="/" class="flex items-center space-x-2">
						<svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
						</svg>
						<span class="text-xl font-semibold text-gray-900 dark:text-white">Alexandria</span>
					</a>
				</div>

				<div class="hidden sm:flex items-center space-x-4">
					<a href="/browse" class="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white px-3 py-2">
						Browse
					</a>
					<a href="/authors" class="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white px-3 py-2">
						Authors
					</a>
					<a href="/series" class="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white px-3 py-2">
						Series
					</a>
					<a href="/piles" class="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white px-3 py-2">
						Piles
					</a>
					<a href="/stats" class="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white px-3 py-2">
						Stats
					</a>
					<a href="/review" class="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white px-3 py-2">
						Review
					</a>
				</div>

				<div class="flex items-center space-x-4">
					<form action="/search" method="GET" class="hidden sm:block">
						<div class="relative">
							<input
								type="search"
								name="q"
								placeholder="Search..."
								class="w-64 pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							/>
							<svg class="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
							</svg>
						</div>
					</form>

					<!-- User menu -->
					{#if data.user}
						<div class="relative">
							<button
								onclick={() => showUserMenu = !showUserMenu}
								class="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
							>
								<div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
									{data.user.display_name?.[0]?.toUpperCase() || data.user.username[0].toUpperCase()}
								</div>
								<span class="hidden md:block text-sm font-medium text-gray-700 dark:text-gray-300">
									{data.user.display_name || data.user.username}
								</span>
								<svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
								</svg>
							</button>

							{#if showUserMenu}
								<div class="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50">
									<div class="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
										<p class="text-sm font-medium text-gray-900 dark:text-white">
											{data.user.display_name || data.user.username}
										</p>
										{#if data.user.email}
											<p class="text-xs text-gray-500 dark:text-gray-400">
												{data.user.email}
											</p>
										{/if}
										{#if data.user.is_admin}
											<p class="text-xs text-blue-600 dark:text-blue-400 font-medium mt-1">
												Administrator
											</p>
										{/if}
									</div>

									<a
										href="/settings"
										class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
										</svg>
										<span>Settings</span>
									</a>

									<button
										onclick={handleLogout}
										class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
										</svg>
										<span>Log out</span>
									</button>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</nav>
	</header>

	<!-- Main content -->
	<main>
		{@render children()}
	</main>

	<!-- Mobile bottom navigation -->
	<nav class="sm:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 z-50">
		<div class="flex justify-around py-2">
			<a href="/" class="flex flex-col items-center px-3 py-2 text-gray-600 dark:text-gray-300">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
				</svg>
				<span class="text-xs">Home</span>
			</a>
			<a href="/browse" class="flex flex-col items-center px-3 py-2 text-gray-600 dark:text-gray-300">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
				</svg>
				<span class="text-xs">Library</span>
			</a>
			<a href="/search" class="flex flex-col items-center px-3 py-2 text-gray-600 dark:text-gray-300">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<span class="text-xs">Search</span>
			</a>
			<a href="/piles" class="flex flex-col items-center px-3 py-2 text-gray-600 dark:text-gray-300">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
				</svg>
				<span class="text-xs">Piles</span>
			</a>
			<a href="/stats" class="flex flex-col items-center px-3 py-2 text-gray-600 dark:text-gray-300">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
				<span class="text-xs">Stats</span>
			</a>
		</div>
	</nav>

	<!-- Spacer for mobile nav -->
	<div class="sm:hidden h-16"></div>
</div>
