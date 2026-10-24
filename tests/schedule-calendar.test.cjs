const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../dashboard/app.js'), 'utf8');
const NOW = Date.parse('2026-10-25T00:00:00Z');
const release = (publish_at, extra = {}) => ({ title: 'Video', publish_at, on_youtube: true, ...extra });
function app(items = []) {
  const calendar = { hidden: true, innerHTML: '', contains: () => true, querySelector: () => ({ focus() {} }),
    addEventListener(type, handler) { this[type] = handler; } };
  class Clock extends Date { static now() { return NOW; } }
  const context = vm.createContext({ Date: Clock, console, window: {},
    document: { addEventListener() {}, getElementById: id => id === 'schedule-calendar' ? calendar : null } });
  const run = code => vm.runInContext(code, context);
  run(source);
  run(`scheduleData = ${JSON.stringify(items)}; scheduleLoaded = true; setupScheduleCalendar(); renderScheduleCalendar();`);
  const click = dataset => calendar.click({ target: { closest: () => ({ dataset }) } });
  return { calendar, run, click };
}

test('Bucharest grouping handles midnight and both sides of the DST change', () => {
  const { run } = app();
  assert.equal(run("calendarDateKey(Date.parse('2026-10-24T22:30:00Z'))"), '2026-10-25');
  assert.equal(run("calendarDateKey(Date.parse('2026-10-25T21:30:00Z'))"), '2026-10-25');
  assert.equal(run("calendarDateKey(Date.parse('2026-10-25T22:30:00Z'))"), '2026-10-26');
  assert.equal(run("calendarDateKey(Date.parse('2026-10-25T00:30:00Z'))"), '2026-10-25');
  assert.equal(run("calendarDateKey(Date.parse('2026-10-25T01:30:00Z'))"), '2026-10-25');
});

test('only future YouTube releases count; stale flags, invalid dates and local plans do not', () => {
  const { calendar } = app([
    release('2026-11-04T18:00:00Z', { is_future: false }),
    release('2026-10-24T18:00:00Z', { is_future: true }),
    release('2026-12-31T18:00:00Z', { on_youtube: false }),
    release('invalid'), release(null), release('2026-10-26T18:00:00Z'),
  ]);
  assert.match(calendar.innerHTML, /2 programări/);
  assert.match(calendar.innerHTML, /4 nov\. 2026, 20:00/);
  assert.doesNotMatch(calendar.innerHTML, /31 dec\./);
});

test('October starts on Thursday and contains all 31 dates, Monday first', () => {
  const { calendar } = app([release('2026-10-26T18:00:00Z')]);
  assert.match(calendar.innerHTML, /<tbody><tr><td><\/td><td><\/td><td><\/td><td><span[^>]*>1<\/span>/);
  assert.equal((calendar.innerHTML.match(/<td>/g) || []).length, 35);
  assert.match(calendar.innerHTML, />31<\/span>/);
});

test('same-day videos and Shorts share a dot and expose their times and safe titles', () => {
  const { calendar, click } = app([
    release('2026-10-26T18:00:00Z', { title: '<img onerror="bad">' }),
    release('2026-10-26T15:00:00Z', { title: 'Short title', kind: 'short' }),
  ]);
  assert.equal((calendar.innerHTML.match(/data-calendar-day="2026-10-26"/g) || []).length, 1);
  click({ calendarDay: '2026-10-26' });
  assert.match(calendar.innerHTML, /2 programări, ultima zi programată/);
  assert.match(calendar.innerHTML, /17:00<\/time>/);
  assert.match(calendar.innerHTML, /20:00<\/time>/);
  assert.match(calendar.innerHTML, /&lt;img onerror=&quot;bad&quot;&gt;/);
  assert.doesNotMatch(calendar.innerHTML, /<img/);
  assert.match(calendar.innerHTML, /<small>Short<\/small>/);
  click({ calendarDay: '2026-10-26' });
  assert.doesNotMatch(calendar.innerHTML, /schedule-calendar-details/);
});

test('last release opens its month and details even across a year boundary', () => {
  const { calendar, click } = app([
    release('2027-01-05T21:00:00Z', { title: 'Last release' }),
    release('2026-10-26T18:00:00Z'),
  ]);
  click({ calendarAction: 'last' });
  assert.match(calendar.innerHTML, /ianuarie 2027/);
  assert.match(calendar.innerHTML, /class="schedule-calendar-day is-last is-selected"/);
  assert.match(calendar.innerHTML, /Last release/);
  click({ calendarAction: 'prev' });
  assert.match(calendar.innerHTML, /decembrie 2026/);
  click({ calendarAction: 'next' });
  assert.match(calendar.innerHTML, /ianuarie 2027/);
});

test('each channel retains its month and uses its own releases', () => {
  const { calendar, run, click } = app([release('2026-11-04T18:00:00Z')]);
  click({ calendarAction: 'next' });
  run(`animeData = ${JSON.stringify([release('2026-10-27T15:00:00Z')])}; currentChannel = 'anime'; renderScheduleCalendar();`);
  assert.match(calendar.innerHTML, /octombrie 2026/);
  assert.match(calendar.innerHTML, /27 oct\. 2026, 17:00/);
  assert.doesNotMatch(calendar.innerHTML, /4 nov\. 2026, 20:00/);
  run("currentChannel = 'dronemill'; renderScheduleCalendar();");
  assert.match(calendar.innerHTML, /noiembrie 2026/);
});

test('loaded empty schedule has an honest empty state; not-yet-loaded channel stays hidden', () => {
  const { calendar, run } = app();
  assert.equal(calendar.hidden, false);
  assert.match(calendar.innerHTML, /Niciun video programat/);
  assert.doesNotMatch(calendar.innerHTML, /data-calendar-action="last"/);
  run("currentChannel = 'anime'; renderScheduleCalendar();");
  assert.equal(calendar.hidden, true);
});

test('published filter keeps the overview and refreshed dates replace the last release', () => {
  const { calendar, run } = app([release('2026-11-04T18:00:00Z')]);
  run("currentFilter = 'published'; renderScheduleCalendar();");
  assert.match(calendar.innerHTML, /1 programare/);
  run(`scheduleData = ${JSON.stringify([release('2026-12-03T18:00:00Z')])}; renderScheduleCalendar();`);
  assert.match(calendar.innerHTML, /3 dec\. 2026, 20:00/);
  assert.doesNotMatch(calendar.innerHTML, /4 nov\./);
});

test('leap February renders day 29 and six-week months keep all rows', () => {
  const { calendar, run } = app();
  run("calendarState.dronemill.month = '2028-02'; renderScheduleCalendar();");
  assert.match(calendar.innerHTML, />29<\/span>/);
  assert.doesNotMatch(calendar.innerHTML, />30<\/span>/);
  run("calendarState.dronemill.month = '2026-11'; renderScheduleCalendar();");
  assert.equal((calendar.innerHTML.match(/<td>/g) || []).length, 42);
});
