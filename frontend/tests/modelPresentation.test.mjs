import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatModelScore, presentModel } from '../src/modelPresentation.ts';

const detection = (score, checks = {}, extra = {}) => ({
  status: 'complete', ai_score: score, check_scores: checks, stability: 'consistent', message: 'Test', ...extra,
});

test('visible metrics preserve near-extreme output without rounding to certainty', () => {
  assert.equal(formatModelScore(.999999), '>99.99');
  assert.equal(formatModelScore(.000001), '<0.01');
  assert.equal(formatModelScore(.236), '23.60');
});

test('different model outputs have different descriptions', () => {
  assert.equal(presentModel(detection(.999)).title, 'Model favors AI-generated');
  assert.equal(presentModel(detection(.001)).title, 'Model favors human-made');
  assert.equal(presentModel(detection(.5)).title, 'No model preference');
});
test('class disagreement is visible even below the old instability threshold', () => {
  const result = presentModel(detection(.49, {'jpeg-85': .51, 'resize-128': .48}));
  assert.equal(result.recheckTitle, 'Re-checks disagree');
  assert.equal(result.checks.length, 3);
});
test('same class is described as agreement, not confidence', () => {
  const result = presentModel(detection(.99, {'jpeg-85': .98, 'resize-128': .96}));
  assert.equal(result.recheckTitle, 'Same model preference');
  assert.match(result.recheckDescription, /does not establish accuracy/);
});
test('missing rechecks never claim agreement', () => {
  assert.equal(presentModel(detection(.99)).recheckTitle, 'Not run');
});
test('missing, invalid and failed output never becomes a class preference', () => {
  for (const score of [null, NaN, Infinity, -1, 2]) {
    assert.equal(presentModel(detection(score)).title, 'No model result');
  }
  assert.equal(presentModel(detection(.9, {}, {status: 'failed'})).title, 'No model result');
  assert.equal(presentModel(detection(null, {}, {status: 'unsupported'})).title, 'This file needs a different detector');
});
