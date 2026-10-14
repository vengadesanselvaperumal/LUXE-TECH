import assert from 'node:assert/strict';
import test from 'node:test';

import { mapNewsCandidates } from '../src/services/newsCandidates.mjs';

test('maps editorial candidates and publisher-attributed article provenance', () => {
  const candidates = mapNewsCandidates([{
    record_type: 'news_derived_candidate',
    name: 'Sculptural Tailoring',
    slug: 'sculptural-tailoring',
    category: 'Silhouettes',
    publisher_count: 2,
    confidence: 99,
    momentum: 98,
    image_url: 'https://example.com/fabricated.jpg',
    articles: [{
      publisher: 'Vogue',
      headline: 'Sculptural Tailoring Dominates Paris Haute Couture Week',
      published_at: '2026-10-12T08:30:00+00:00',
      article_url: 'https://www.vogue.com/article/sculptural-tailoring-paris',
    }],
  }]);

  assert.deepEqual(candidates, [{
    key: 'sculptural-tailoring',
    name: 'Sculptural Tailoring',
    category: 'Silhouettes',
    publisherCount: 2,
    sourceLabel: 'News-derived',
    articles: [{
      publisher: 'Vogue',
      headline: 'Sculptural Tailoring Dominates Paris Haute Couture Week',
      publishedAt: '2026-10-12T08:30:00+00:00',
      articleUrl: 'https://www.vogue.com/article/sculptural-tailoring-paris',
    }],
  }]);
});

test('returns an empty list for empty or malformed candidate responses', () => {
  assert.deepEqual(mapNewsCandidates([]), []);
  assert.deepEqual(mapNewsCandidates(null), []);
  assert.deepEqual(mapNewsCandidates([{
    name: 'Unattributed topic',
    category: 'Color',
    articles: [{
      publisher: 'Unknown',
      headline: 'No canonical publisher link',
      article_url: 'http://example.com/article',
    }],
  }]), []);
});

test('drops article provenance without a publisher, headline, or HTTPS source link', () => {
  const [candidate] = mapNewsCandidates([{
    name: 'Tailoring',
    category: 'Silhouettes',
    articles: [
      {
        publisher: 'Vogue',
        headline: 'A source-backed headline',
        published_at: null,
        article_url: 'https://www.vogue.com/article/tailoring',
      },
      {
        publisher: 'Unverified',
        headline: 'Insecure link',
        article_url: 'http://example.com/article',
      },
    ],
  }]);

  assert.equal(candidate.publisherCount, 1);
  assert.equal(candidate.articles.length, 1);
  assert.equal(candidate.articles[0].publishedAt, null);
  assert.equal(candidate.articles[0].articleUrl, 'https://www.vogue.com/article/tailoring');
});

test('chooses the lead article image based on topic relevance, not first article order', () => {
  const [candidate] = mapNewsCandidates([{
    name: 'Tactile Suede & Heritage Leather',
    slug: 'tactile-suede-heritage-leather',
    category: 'Textures',
    articles: [
      {
        publisher: 'Vogue',
        headline: 'How Hugo Marchand Became One of Ballet’s Brightest Stars',
        published_at: '2026-10-10T10:00:00+00:00',
        article_url: 'https://www.vogue.com/article/hugo-marchand-ballet',
        image_url: 'https://assets.vogue.com/ballet-portrait.jpg',
      },
      {
        publisher: "Harper's Bazaar",
        headline: 'The 10 Best Suede Jackets and Heritage Leather Coats for Fall',
        published_at: '2026-10-11T12:00:00+00:00',
        article_url: 'https://www.harpersbazaar.com/fashion/suede-jackets',
        image_url: 'https://assets.harpersbazaar.com/suede-leather-coat.jpg',
      },
    ],
  }]);

  assert.equal(candidate.imageUrl, 'https://assets.harpersbazaar.com/suede-leather-coat.jpg');
  assert.equal(candidate.articles.length, 2);
  // Verify provenance is preserved
  assert.equal(candidate.articles[0].publisher, 'Vogue');
  assert.equal(candidate.articles[1].publisher, "Harper's Bazaar");
});

test('leaves imageUrl undefined when all articles are off-topic or lack relevant imagery', () => {
  const [candidate] = mapNewsCandidates([{
    name: 'Architectural Footwear & Statement Bags',
    slug: 'architectural-footwear-statement-bags',
    category: 'Accessories',
    articles: [
      {
        publisher: 'Medical Daily',
        headline: 'Under-eye bag surgery procedures double in 2026',
        published_at: '2026-10-10T10:00:00+00:00',
        article_url: 'https://example.com/surgery-report',
        image_url: 'https://example.com/clinic.jpg',
      },
    ],
  }]);

  assert.equal(candidate.imageUrl, undefined);
  assert.equal(candidate.articles.length, 1);
});
