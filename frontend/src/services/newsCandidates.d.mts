export type NewsCandidateArticle = {
  publisher: string;
  headline: string;
  publishedAt: string | null;
  articleUrl: string;
  imageUrl: string | null;
};

export type NewsDerivedCandidate = {
  key: string;
  id?: string;
  slug?: string;
  name: string;
  category: string;
  season?: string;
  description?: string;
  confidence?: number;
  momentum?: number;
  velocity?: number;
  acceleration?: number;
  dna?: Record<string, any>;
  data_status?: string;
  is_candidate?: boolean;
  publisherCount: number;
  sourceLabel: 'News-derived';
  imageUrl?: string | null;
  image_url?: string | null;
  articles: NewsCandidateArticle[];
};

export function mapNewsCandidates(response: unknown): NewsDerivedCandidate[];
