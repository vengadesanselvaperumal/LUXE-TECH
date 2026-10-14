import assert from 'node:assert/strict';
import test from 'node:test';

import { candidateToTrendRecord, getArchetypeDna } from '../src/services/trendCandidateMapping.mjs';

test('enriches candidate trend record with signals, observation counts, and publisher provenance', () => {
  const candidate = {
    key: 'sculptural-tailoring-silhouettes-0',
    name: 'Sculptural Tailoring & Suiting',
    category: 'Silhouettes',
    publisherCount: 2,
    sourceLabel: 'News-derived',
    imageUrl: 'https://assets.vogue.com/sculptural.jpg',
    articles: [
      {
        publisher: 'Vogue',
        headline: 'Sculptural Tailoring Dominates Paris Haute Couture Week',
        publishedAt: '2026-10-12T08:30:00+00:00',
        articleUrl: 'https://www.vogue.com/article/sculptural-tailoring-paris',
        imageUrl: 'https://assets.vogue.com/sculptural.jpg',
      },
      {
        publisher: "Harper's Bazaar",
        headline: 'How to Style Sculptural Tailoring and Oversized Blazers',
        publishedAt: '2026-10-11T22:00:00+00:00',
        articleUrl: 'https://www.harpersbazaar.com/fashion/trends/sculptural-tailoring-guide',
      },
    ],
  };

  const record = candidateToTrendRecord(candidate);

  assert.equal(record.id, 'sculptural-tailoring-silhouettes-0');
  assert.equal(record.slug, 'sculptural-tailoring-silhouettes-0');
  assert.equal(record.name, 'Sculptural Tailoring & Suiting');
  assert.equal(record.category, 'Silhouettes');
  assert.equal(record.data_status, 'news_derived');
  assert.equal(record.is_candidate, true);
  assert.equal(record.observationCount, 2);
  assert.equal(record.publisherCount, 2);
  assert.equal(record.signals.length, 2);

  // Provenance checks
  assert.equal(record.signals[0].metadata.source_name, 'Vogue');
  assert.equal(record.signals[0].metadata.source_url, 'https://www.vogue.com/article/sculptural-tailoring-paris');
  assert.equal(record.signals[0].metadata.article_title, 'Sculptural Tailoring Dominates Paris Haute Couture Week');
  assert.equal(record.signals[0].source, 'culture');
  assert.equal(record.signals[0].signal_type, 'news_derived');

  assert.equal(record.signals[1].metadata.source_name, "Harper's Bazaar");
  assert.equal(record.signals[1].metadata.source_url, 'https://www.harpersbazaar.com/fashion/trends/sculptural-tailoring-guide');

  // Empirical telemetry integrity: editorial candidates have no synthetic scores
  assert.equal(record.signals[0].strength, null);
  assert.equal(record.signals[1].strength, null);
  assert.equal(record.cross_source_agreement, null);
  assert.equal(record.momentum, null);
  assert.equal(record.velocity, null);
  assert.equal(record.confidence, null);

  // DNA checks
  assert.ok(record.dna.colors.length > 0);
  assert.ok(record.dna.materials.length > 0);
  assert.ok(record.dna.textures.length > 0);
  assert.ok(record.dna.silhouettes.length > 0);
  assert.ok(record.dna.patterns.length > 0);
  assert.equal(record.dna.materials[0], 'Double-Faced Wool Twill');
});

test('assigns authentic visual DNA by theme archetype and category', () => {
  const materialsDna = getArchetypeDna('Sheer & Translucent Layering', 'Materials');
  assert.ok(materialsDna.materials.includes('Silk Organza'));
  assert.ok(materialsDna.textures.includes('Translucent Veil'));

  const colorDna = getArchetypeDna('Butter Yellow & Warm Pastels', 'Color');
  assert.ok(colorDna.colors.some(c => c.hex === '#FFF3B0'));

  const burgundyDna = getArchetypeDna('Deep Burgundy & Oxblood Accents', 'Color');
  assert.ok(burgundyDna.colors.some(c => c.hex === '#58111A'));

  const genericAccessories = getArchetypeDna('Minimalist Leather', 'Accessories');
  assert.ok(genericAccessories.materials.includes('Spazzolato Box Leather'));
});

