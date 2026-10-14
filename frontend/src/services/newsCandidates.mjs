function isHttpsUrl(value) {
  if (typeof value !== 'string') return false;

  try {
    return new URL(value).protocol === 'https:';
  } catch {
    return false;
  }
}

const ARCHETYPE_IMAGE_KEYWORDS = {
  'Sculptural Tailoring & Suiting': ['tailoring', 'blazer', 'suit', 'suiting', 'trousers', 'jacket', 'coat', 'silhouette'],
  'Sheer & Translucent Layering': ['sheer', 'organza', 'chiffon', 'mesh', 'translucent', 'gauze', 'tulle', 'transparent'],
  'Butter Yellow & Warm Pastels': ['butter yellow', 'yellow', 'pastel', 'lemon', 'vanilla', 'ochre'],
  'Deep Burgundy & Oxblood Accents': ['burgundy', 'oxblood', 'wine', 'crimson', 'cherry red', 'bordeaux'],
  'Tactile Suede & Heritage Leather': ['suede', 'leather', 'shearling', 'fringe', 'calfskin', 'hide'],
  'Artisanal Knitwear & Open Weave': ['knit', 'knitwear', 'crochet', 'wool', 'cashmere', 'cardigan', 'sweater', 'alpaca', 'boucle'],
  'Raw Denim & Chambray Structures': ['denim', 'jeans', 'chambray', 'selvedge', 'indigo'],
  'Supple Leather & Polished Skins': ['leather', 'calfskin', 'nappa', 'patent leather', 'skins', 'supple'],
  'Liquid Silk & Satin Fluidity': ['silk', 'satin', 'slip dress', 'charmeuse', 'draped', 'viscose'],
  'Brushed Wool & Cashmere Tailoring': ['wool', 'cashmere', 'flannel', 'gabardine', 'tweed', 'overcoat'],
  'Utility Workwear & Structured Outerwear': ['utility', 'workwear', 'cargo', 'outerwear', 'bomber', 'trench'],
  'Dark Romance & Gothic Elegance': ['dark romance', 'gothic', 'corset', 'lace', 'velvet', 'victorian'],
  'Architectural Footwear & Statement Bags': ['shoes', 'boots', 'loafers', 'bag', 'bags', 'handbag', 'handbags', 'tote', 'heels', 'sneakers', 'footwear', 'it bag', 'statement bag'],
};

const OFF_TOPIC_PENALTIES = [
  'surgery', 'blepharoplasty', 'botox', 'clinic', 'hospital', 'medical', 'cosmetic procedure',
  'ballet', 'dancer', 'opera', 'theatre',
  'recipe', 'kitchen', 'cooking', 'cocktail',
  'election', 'senate', 'politics', 'court', 'trial',
  'divorce', 'dating', 'relationship',
];

export function scoreArticleRelevance(article, candidateName, category) {
  if (!article || !isHttpsUrl(article.imageUrl)) return -Infinity;

  const headline = (article.headline || '').toLowerCase();
  const articleUrl = (article.articleUrl || '').toLowerCase();
  const corpus = `${headline} ${articleUrl}`;

  // Off-topic penalty
  let penalty = 0;
  for (const term of OFF_TOPIC_PENALTIES) {
    if (corpus.includes(term)) {
      penalty += 50;
    }
  }

  // Determine topic keywords to match
  let targetKeywords = ARCHETYPE_IMAGE_KEYWORDS[candidateName] || [];
  if (targetKeywords.length === 0) {
    const nameWords = (candidateName || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 2 && !['and', 'the', 'for', 'with', 'structures', 'accents'].includes(w));
    targetKeywords = [...nameWords, (category || '').toLowerCase()].filter(Boolean);
  }

  let matchScore = 0;
  for (const kw of targetKeywords) {
    const kwLower = kw.toLowerCase();
    const regex = new RegExp(`\\b${kwLower.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}(?:s|es)?\\b`, 'i');
    if (regex.test(headline)) {
      matchScore += 15;
    } else if (regex.test(articleUrl)) {
      matchScore += 8;
    } else if (corpus.includes(kwLower)) {
      matchScore += 4;
    }
  }

  return matchScore - penalty;
}

export function findMostRelevantArticleImage(candidateName, category, articles) {
  if (!Array.isArray(articles) || articles.length === 0) return null;

  let bestScore = 0;
  let bestImage = null;

  for (const article of articles) {
    const score = scoreArticleRelevance(article, candidateName, category);
    if (score > bestScore) {
      bestScore = score;
      bestImage = article.imageUrl;
    }
  }

  return bestImage;
}

export function mapNewsCandidates(response) {
  if (!Array.isArray(response)) return [];

  return response.flatMap((candidate, index) => {
    if (
      !candidate ||
      typeof candidate.name !== 'string' ||
      !candidate.name.trim() ||
      typeof candidate.category !== 'string' ||
      !candidate.category.trim()
    ) {
      return [];
    }

    const articles = Array.isArray(candidate.articles)
      ? candidate.articles.flatMap(article => {
          if (
            !article ||
            typeof article.publisher !== 'string' ||
            !article.publisher.trim() ||
            typeof article.headline !== 'string' ||
            !article.headline.trim() ||
            !isHttpsUrl(article.article_url)
          ) {
            return [];
          }

          return [{
            publisher: article.publisher.trim(),
            headline: article.headline.trim(),
            publishedAt: typeof article.published_at === 'string' ? article.published_at : null,
            articleUrl: article.article_url,
            ...(isHttpsUrl(article.image_url) ? { imageUrl: article.image_url } : {}),
          }];
        })
      : [];

    if (articles.length === 0) return [];

    const publisherCount = Number.isInteger(candidate.publisher_count) && candidate.publisher_count >= 0
      ? candidate.publisher_count
      : new Set(articles.map(article => article.publisher)).size;

    const key = typeof candidate.slug === 'string' && candidate.slug
      ? candidate.slug
      : `${candidate.name}-${candidate.category}-${index}`;

    const leadImageUrl = findMostRelevantArticleImage(candidate.name.trim(), candidate.category.trim(), articles);

    return [{
      key,
      name: candidate.name.trim(),
      category: candidate.category.trim(),
      publisherCount,
      sourceLabel: 'News-derived',
      ...(leadImageUrl ? { imageUrl: leadImageUrl } : {}),
      articles,
    }];
  });
}

