import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  dateKey,
  zonedInstant,
  localInput,
  intersect,
  freeWindows,
  addDays,
} from '../apps/web/src/lib/calendar-time.ts';
const zone = 'America/Edmonton';
test('full-date keys distinguish the same day in different months', () => {
  assert.notEqual(
    dateKey(zonedInstant('2026-11-09', '08:00')),
    dateKey(zonedInstant('2026-12-09', '08:00')),
  );
  assert.equal(
    intersect(
      zonedInstant('2026-12-09', '08:00'),
      zonedInstant('2026-12-09', '12:00'),
      '2026-11-09',
    ),
    null,
  );
});
test('actual free windows subtract both busy time and confirmed work', () => {
  const at = (time: string) => zonedInstant('2026-11-09', time);
  const result = freeWindows(
    [{ starts_at: at('08:00'), ends_at: at('17:00') }],
    [
      { starts_at: at('08:00'), ends_at: at('10:00') },
      { starts_at: at('12:00'), ends_at: at('14:00') },
    ],
  );
  assert.deepEqual(result, [
    { starts_at: at('10:00'), ends_at: at('12:00') },
    { starts_at: at('14:00'), ends_at: at('17:00') },
  ]);
});
test('multi-day blockers clip each intersecting day using half-open bounds', () => {
  const start = zonedInstant('2026-11-09', '17:00'),
    end = zonedInstant('2026-11-11', '00:00');
  assert.deepEqual(intersect(start, end, '2026-11-10'), {
    starts_at: zonedInstant('2026-11-10'),
    ends_at: zonedInstant('2026-11-11'),
  });
  assert.equal(intersect(start, end, '2026-11-11'), null);
});
test('calendar conversions round-trip local dates across seasons and month boundaries', () => {
  for (const date of ['2026-01-15', '2026-06-15', '2026-11-09'])
    assert.equal(localInput(zonedInstant(date, '08:30', zone), zone), date + 'T08:30');
  assert.equal(addDays('2026-11-30', 1), '2026-12-01');
});
