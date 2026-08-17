export interface Genre {
  slug: string;
  label: string;
  eyebrow: string;
  description: string;
  themeClass: string;
}

export const GENRES: readonly Genre[] = [
  {
    slug: 'horror',
    label: 'Horror',
    eyebrow: 'Enter if you dare',
    description: 'Hauntings, monsters, uncanny places, and the things waiting just beyond the light.',
    themeClass: 'genre-horror'
  },
  {
    slug: 'fantasy',
    label: 'Fantasy',
    eyebrow: 'Beyond the known world',
    description: 'Impossible quests, dangerous magic, strange kingdoms, and worlds with rules all their own.',
    themeClass: 'genre-fantasy'
  },
  {
    slug: 'science-fiction',
    label: 'Science Fiction',
    eyebrow: 'The future is unwritten',
    description: 'Distant worlds, altered futures, impossible technologies, and questions larger than humanity.',
    themeClass: 'genre-science-fiction'
  },
  {
    slug: 'mystery',
    label: 'Mystery',
    eyebrow: 'Every detail matters',
    description: 'Hidden motives, missing pieces, clever investigators, and truths that refuse to stay buried.',
    themeClass: 'genre-mystery'
  },
  {
    slug: 'thriller',
    label: 'Thriller',
    eyebrow: 'No time to look back',
    description: 'High stakes, tightening traps, dangerous conspiracies, and stories built to keep you moving.',
    themeClass: 'genre-thriller'
  },
  {
    slug: 'romance',
    label: 'Romance',
    eyebrow: 'The heart has plans',
    description: 'Yearning, wit, second chances, and the wonderfully complicated business of falling in love.',
    themeClass: 'genre-romance'
  },
  {
    slug: 'historical-fiction',
    label: 'Historical Fiction',
    eyebrow: 'The past, reimagined',
    description: 'Private lives set against vanished worlds, turbulent eras, and history in motion.',
    themeClass: 'genre-historical-fiction'
  },
  {
    slug: 'literary-fiction',
    label: 'Literary Fiction',
    eyebrow: 'Stories that linger',
    description: 'Ambitious voices, intimate lives, and novels drawn to the difficult texture of being human.',
    themeClass: 'genre-literary-fiction'
  },
  {
    slug: 'biography-memoir',
    label: 'Biography & Memoir',
    eyebrow: 'A life, closely read',
    description: 'Remarkable lives, candid recollections, and the experiences that shape a person.',
    themeClass: 'genre-biography-memoir'
  },
  {
    slug: 'history',
    label: 'History',
    eyebrow: 'How we arrived here',
    description: 'Civilizations, conflicts, movements, and the people who changed what came next.',
    themeClass: 'genre-history'
  },
  {
    slug: 'young-adult',
    label: 'Young Adult',
    eyebrow: 'Everything is changing',
    description: 'First choices, fierce friendships, new worlds, and the stories that meet you in between.',
    themeClass: 'genre-young-adult'
  }
];
