// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces

export interface User {
	id: number;
	username: string;
	email: string | null;
	display_name: string | null;
	is_admin: boolean;
	can_download: boolean;
	created_at: string;
	last_login: string | null;
}

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			user: User | null;
		}
		interface PageData {
			user?: User | null;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
