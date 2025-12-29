/**
 * Formatting utilities for display values
 */

/**
 * Map of ISO 639-1 language codes to full language names
 */
const LANGUAGE_NAMES: Record<string, string> = {
	en: 'English',
	es: 'Spanish',
	fr: 'French',
	de: 'German',
	it: 'Italian',
	pt: 'Portuguese',
	ru: 'Russian',
	zh: 'Chinese',
	ja: 'Japanese',
	ko: 'Korean',
	ar: 'Arabic',
	hi: 'Hindi',
	nl: 'Dutch',
	sv: 'Swedish',
	no: 'Norwegian',
	da: 'Danish',
	fi: 'Finnish',
	pl: 'Polish',
	cs: 'Czech',
	el: 'Greek',
	he: 'Hebrew',
	tr: 'Turkish',
	th: 'Thai',
	vi: 'Vietnamese',
	id: 'Indonesian',
	ms: 'Malay',
	tl: 'Tagalog',
	uk: 'Ukrainian',
	ro: 'Romanian',
	hu: 'Hungarian',
	bg: 'Bulgarian',
	hr: 'Croatian',
	sk: 'Slovak',
	sl: 'Slovenian',
	sr: 'Serbian',
	lt: 'Lithuanian',
	lv: 'Latvian',
	et: 'Estonian',
	fa: 'Persian',
	ur: 'Urdu',
	bn: 'Bengali',
	ta: 'Tamil',
	te: 'Telugu',
	mr: 'Marathi',
	gu: 'Gujarati',
	kn: 'Kannada',
	ml: 'Malayalam',
	pa: 'Punjabi',
	sw: 'Swahili',
	af: 'Afrikaans',
	ca: 'Catalan',
	eu: 'Basque',
	gl: 'Galician',
	cy: 'Welsh',
	ga: 'Irish',
	la: 'Latin',
	grc: 'Ancient Greek',
	ang: 'Old English',
	// Extended codes sometimes used
	'en-US': 'English (US)',
	'en-GB': 'English (UK)',
	'en-AU': 'English (Australian)',
	'pt-BR': 'Portuguese (Brazilian)',
	'zh-CN': 'Chinese (Simplified)',
	'zh-TW': 'Chinese (Traditional)',
	eng: 'English',
	spa: 'Spanish',
	fre: 'French',
	fra: 'French',
	ger: 'German',
	deu: 'German',
	ita: 'Italian',
	por: 'Portuguese',
	rus: 'Russian',
	chi: 'Chinese',
	zho: 'Chinese',
	jpn: 'Japanese',
	kor: 'Korean',
	ara: 'Arabic',
	hin: 'Hindi',
	dut: 'Dutch',
	nld: 'Dutch'
};

/**
 * Convert a language code to its full name
 * @param code - ISO 639-1 or 639-2 language code
 * @returns Full language name, or the original code if not found
 */
export function getLanguageName(code: string | null | undefined): string {
	if (!code) return '';
	const normalised = code.toLowerCase().trim();
	return LANGUAGE_NAMES[normalised] || code;
}

/**
 * DDC (Dewey Decimal Classification) top-level categories
 */
const DDC_CATEGORIES: Record<string, string> = {
	'0': 'Computer Science, Information & General Works',
	'1': 'Philosophy & Psychology',
	'2': 'Religion',
	'3': 'Social Sciences',
	'4': 'Language',
	'5': 'Science',
	'6': 'Technology',
	'7': 'Arts & Recreation',
	'8': 'Literature',
	'9': 'History & Geography'
};

/**
 * DDC second-level (division) categories for more specific descriptions
 */
const DDC_DIVISIONS: Record<string, string> = {
	'00': 'Computer Science, Knowledge & Systems',
	'01': 'Bibliographies',
	'02': 'Library & Information Sciences',
	'03': 'Encyclopaedias & Books of Facts',
	'04': 'Data Processing & Computer Science',
	'05': 'Magazines, Journals & Serials',
	'06': 'Associations, Organisations & Museums',
	'07': 'News Media, Journalism & Publishing',
	'08': 'Quotations',
	'09': 'Manuscripts & Rare Books',
	'10': 'Philosophy',
	'11': 'Metaphysics',
	'12': 'Epistemology',
	'13': 'Parapsychology & Occultism',
	'14': 'Philosophical Schools of Thought',
	'15': 'Psychology',
	'16': 'Logic',
	'17': 'Ethics',
	'18': 'Ancient, Medieval & Eastern Philosophy',
	'19': 'Modern Western Philosophy',
	'20': 'Religion',
	'21': 'Philosophy of Religion',
	'22': 'The Bible',
	'23': 'Christianity & Christian Theology',
	'24': 'Christian Practice & Observance',
	'25': 'Christian Pastoral Practice',
	'26': 'Christian Organisation & Social Work',
	'27': 'History of Christianity',
	'28': 'Christian Denominations',
	'29': 'Other Religions',
	'30': 'Social Sciences, Sociology & Anthropology',
	'31': 'Statistics',
	'32': 'Political Science',
	'33': 'Economics',
	'34': 'Law',
	'35': 'Public Administration & Military Science',
	'36': 'Social Problems & Social Services',
	'37': 'Education',
	'38': 'Commerce, Communications & Transport',
	'39': 'Customs, Etiquette & Folklore',
	'40': 'Language',
	'41': 'Linguistics',
	'42': 'English & Old English Languages',
	'43': 'German & Related Languages',
	'44': 'French & Related Languages',
	'45': 'Italian, Romanian & Related Languages',
	'46': 'Spanish & Portuguese Languages',
	'47': 'Latin & Italic Languages',
	'48': 'Classical & Modern Greek Languages',
	'49': 'Other Languages',
	'50': 'Science',
	'51': 'Mathematics',
	'52': 'Astronomy',
	'53': 'Physics',
	'54': 'Chemistry',
	'55': 'Earth Sciences & Geology',
	'56': 'Fossils & Prehistoric Life',
	'57': 'Life Sciences, Biology',
	'58': 'Plants (Botany)',
	'59': 'Animals (Zoology)',
	'60': 'Technology',
	'61': 'Medicine & Health',
	'62': 'Engineering',
	'63': 'Agriculture',
	'64': 'Home & Family Management',
	'65': 'Management & Public Relations',
	'66': 'Chemical Engineering',
	'67': 'Manufacturing',
	'68': 'Manufacture for Specific Uses',
	'69': 'Building & Construction',
	'70': 'Arts',
	'71': 'Landscaping & Area Planning',
	'72': 'Architecture',
	'73': 'Sculpture, Ceramics & Metalwork',
	'74': 'Drawing & Decorative Arts',
	'75': 'Painting',
	'76': 'Graphic Arts',
	'77': 'Photography & Computer Art',
	'78': 'Music',
	'79': 'Sports, Games & Entertainment',
	'80': 'Literature, Rhetoric & Criticism',
	'81': 'American Literature in English',
	'82': 'English & Old English Literatures',
	'83': 'German & Related Literatures',
	'84': 'French & Related Literatures',
	'85': 'Italian, Romanian & Related Literatures',
	'86': 'Spanish & Portuguese Literatures',
	'87': 'Latin & Italic Literatures',
	'88': 'Classical & Modern Greek Literatures',
	'89': 'Other Literatures',
	'90': 'History',
	'91': 'Geography & Travel',
	'92': 'Biography & Genealogy',
	'93': 'History of the Ancient World',
	'94': 'European History',
	'95': 'Asian History',
	'96': 'African History',
	'97': 'North American History',
	'98': 'South American History',
	'99': 'History of Other Areas'
};

export interface DdcInfo {
	code: string;
	category: string;
	division?: string;
}

/**
 * Get DDC category information from a classification code
 * @param code - DDC classification code (e.g., "004", "823.914", "Fiction")
 * @returns Object with code and category/division names
 */
export function getDdcInfo(code: string | null | undefined): DdcInfo | null {
	if (!code) return null;

	// Handle "Fiction" category (not a DDC code)
	if (code.toLowerCase() === 'fiction') {
		return {
			code: 'Fiction',
			category: 'Fiction'
		};
	}

	// Extract numeric part (handle codes like "823.914")
	const numericMatch = code.match(/^(\d+)/);
	if (!numericMatch) return null;

	const numericPart = numericMatch[1];
	const firstDigit = numericPart.charAt(0);
	// Ensure we have at least 2 digits for the division lookup
	const firstTwo = numericPart.substring(0, 2);
	const firstTwoDigits = firstTwo.length === 1 ? firstTwo + '0' : firstTwo;

	const category = DDC_CATEGORIES[firstDigit];
	const division = DDC_DIVISIONS[firstTwoDigits];

	if (!category) return null;

	return {
		code,
		category,
		division: division !== category ? division : undefined
	};
}

/**
 * Format DDC code with category name for display
 * @param code - DDC classification code
 * @returns Formatted string like "823.914 (English Literature)"
 */
export function formatDdcDisplay(code: string | null | undefined): string {
	const info = getDdcInfo(code);
	if (!info) return code || '';

	if (info.code.toLowerCase() === 'fiction') {
		return 'Fiction';
	}

	// Prefer division (more specific) over category
	const categoryName = info.division || info.category;
	return `${info.code} (${categoryName})`;
}
