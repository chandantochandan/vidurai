/**
 * EdgeFilter Manual Test
 *
 * Tests the EdgeFilter functionality.
 *
 * Usage:
 *   npx ts-node src/filter/__tests__/manual_test.ts
 */

import { EdgeFilter, FilterableEvent, shouldIgnoreFile } from '../EdgeFilter';

// Test utilities
let testsPassed = 0;
let testsFailed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) {
    testsPassed++;
    console.log(`  PASS: ${message}`);
  } else {
    testsFailed++;
    console.log(`  FAIL: ${message}`);
  }
}

function assertEquals<T>(actual: T, expected: T, message: string): void {
  assert(actual === expected, `${message} (expected ${expected}, got ${actual})`);
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  console.log('='.repeat(60));
  console.log('EDGE FILTER MANUAL TEST');
  console.log('='.repeat(60));
  console.log('');

  // Test 1: Smart File Filtering
  console.log('TEST 1: Smart File Filtering');
  {
    const filter = new EdgeFilter({ debug: false });
    const emitted: FilterableEvent[] = [];
    filter.on('event', (e: FilterableEvent) => emitted.push(e));

    filter.submit({ type: 'file_edit', file: '/project/node_modules/lodash/index.js' });
    filter.submit({ type: 'file_edit', file: '/project/.git/HEAD' });
    filter.submit({ type: 'file_edit', file: '/project/dist/bundle.js' });
    filter.submit({ type: 'file_edit', file: '/project/build/app.js' });
    filter.submit({ type: 'file_edit', file: '/project/file.tmp' });

    filter.flush();

    assertEquals(emitted.length, 0, 'All ignored files should be filtered');
    assertEquals(filter.getStats().filtered, 5, 'Should have filtered 5 files');
    filter.destroy();
  }
  console.log('');

  // Test 2: Pass normal files
  console.log('TEST 2: Pass Normal Source Files');
  {
    const filter = new EdgeFilter({ debug: false, enableBatching: false });
    const emitted: FilterableEvent[] = [];
    filter.on('event', (e: FilterableEvent) => emitted.push(e));

    filter.submit({ type: 'file_edit', file: '/project/src/index.ts' });
    filter.flush();

    assertEquals(emitted.length, 1, 'Normal files should pass');
    assertEquals(filter.getStats().passed, 1, 'Should have passed 1 file');
    filter.destroy();
  }
  console.log('');

  // Test 3: Debouncing
  console.log('TEST 3: Debouncing Rapid Edits');
  {
    const filter = new EdgeFilter({
      debug: false,
      debounceDelay: 100,
      enableBatching: false,
    });
    const emitted: FilterableEvent[] = [];
    filter.on('event', (e: FilterableEvent) => emitted.push(e));

    // Submit 5 rapid edits to same file
    for (let i = 0; i < 5; i++) {
      filter.submit({
        type: 'file_edit',
        file: '/project/src/app.ts',
        data: { gist: `Edit ${i}` },
      });
    }

    assertEquals(emitted.length, 0, 'Events should be debounced initially');

    // Wait for debounce
    await sleep(150);

    assertEquals(emitted.length, 1, 'Should emit single event after debounce');
    assertEquals(filter.getStats().debounced, 4, 'Should have debounced 4 events');
    filter.destroy();
  }
  console.log('');

  // Test 4: Deduplication
  console.log('TEST 4: Deduplication');
  {
    const filter = new EdgeFilter({
      debug: false,
      enableBatching: false,
      debounceDelay: 0,
    });
    const emitted: FilterableEvent[] = [];
    filter.on('event', (e: FilterableEvent) => emitted.push(e));

    // Submit same focus event twice
    filter.submit({ type: 'focus', file: '/project/src/app.ts' });
    filter.submit({ type: 'focus', file: '/project/src/app.ts' });

    assertEquals(emitted.length, 1, 'Duplicate events should be deduplicated');
    assertEquals(filter.getStats().deduplicated, 1, 'Should have deduplicated 1 event');
    filter.destroy();
  }
  console.log('');

  // Test 5: Rate Limiting
  console.log('TEST 5: Rate Limiting');
  {
    const filter = new EdgeFilter({
      debug: false,
      maxEventsPerSecond: 5,
      enableBatching: false,
      enableSmartFilter: false,
      debounceDelay: 0,
    });
    const emitted: FilterableEvent[] = [];
    filter.on('event', (e: FilterableEvent) => emitted.push(e));

    // Submit 10 events rapidly
    for (let i = 0; i < 10; i++) {
      filter.submit({ type: 'terminal', data: { command: `cmd${i}` } });
    }

    assertEquals(filter.getStats().rateLimited, 5, 'Should have rate limited 5 events');
    filter.destroy();
  }
  console.log('');

  // Test 6: Batching
  console.log('TEST 6: Batching');
  {
    const filter = new EdgeFilter({
      debug: false,
      enableBatching: true,
      batchWindow: 50,
      maxBatchSize: 10,
      enableSmartFilter: false,
      debounceDelay: 0,
    });
    const batches: FilterableEvent[][] = [];
    filter.on('batch', (events: FilterableEvent[]) => batches.push(events));

    filter.submit({ type: 'terminal', data: { command: 'cmd1' } });
    filter.submit({ type: 'terminal', data: { command: 'cmd2' } });
    filter.submit({ type: 'terminal', data: { command: 'cmd3' } });

    await sleep(100);

    assertEquals(batches.length, 1, 'Should emit one batch');
    assertEquals(batches[0]?.length || 0, 3, 'Batch should contain 3 events');
    filter.destroy();
  }
  console.log('');

  // Test 7: Flush
  console.log('TEST 7: Flush Pending Events');
  {
    const filter = new EdgeFilter({
      debug: false,
      debounceDelay: 10000, // Long delay
      enableBatching: false,
    });
    const emitted: FilterableEvent[] = [];
    filter.on('event', (e: FilterableEvent) => emitted.push(e));

    filter.submit({ type: 'file_edit', file: '/project/src/a.ts' });
    filter.submit({ type: 'file_edit', file: '/project/src/b.ts' });

    assertEquals(emitted.length, 0, 'Events should be pending');

    filter.flush();

    assertEquals(emitted.length, 2, 'Flush should emit all pending events');
    filter.destroy();
  }
  console.log('');

  // Test 8: shouldIgnoreFile utility
  console.log('TEST 8: shouldIgnoreFile Utility');
  {
    assert(shouldIgnoreFile('/project/node_modules/lodash/index.js'), 'node_modules should be ignored');
    assert(shouldIgnoreFile('C:\\project\\node_modules\\lodash\\index.js'), 'Windows node_modules should be ignored');
    assert(shouldIgnoreFile('/project/.git/HEAD'), '.git should be ignored');
    assert(shouldIgnoreFile('/project/package-lock.json'), 'package-lock.json should be ignored');
    assert(shouldIgnoreFile('/project/file.tmp'), '.tmp files should be ignored');
    assert(!shouldIgnoreFile('/project/src/app.ts'), 'Source files should NOT be ignored');
    assert(!shouldIgnoreFile('/project/README.md'), 'README should NOT be ignored');
  }
  console.log('');

  // Test 9: Statistics
  console.log('TEST 9: Statistics');
  {
    const filter = new EdgeFilter({ debug: false });
    const stats = filter.getStats();

    assert('received' in stats, 'Stats should have received');
    assert('passed' in stats, 'Stats should have passed');
    assert('debounced' in stats, 'Stats should have debounced');
    assert('deduplicated' in stats, 'Stats should have deduplicated');
    assert('rateLimited' in stats, 'Stats should have rateLimited');
    assert('filtered' in stats, 'Stats should have filtered');
    assert('batched' in stats, 'Stats should have batched');

    filter.submit({ type: 'file_edit', file: '/project/node_modules/x' });
    assertEquals(filter.getStats().received, 1, 'Should track received');

    filter.resetStats();
    assertEquals(filter.getStats().received, 0, 'Reset should clear stats');

    filter.destroy();
  }
  console.log('');

  // Summary
  console.log('='.repeat(60));
  console.log(`TESTS COMPLETE: ${testsPassed} passed, ${testsFailed} failed`);
  console.log('='.repeat(60));

  process.exit(testsFailed > 0 ? 1 : 0);
}

main().catch(console.error);
