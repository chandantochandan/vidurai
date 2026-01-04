/**
 * EdgeFilter Tests
 */

import { EdgeFilter, FilterableEvent, shouldIgnoreFile } from '../EdgeFilter';

describe('EdgeFilter', () => {
  let filter: EdgeFilter;

  beforeEach(() => {
    filter = new EdgeFilter({ debug: false });
  });

  afterEach(() => {
    filter.destroy();
  });

  describe('Smart File Filtering', () => {
    test('ignores node_modules', () => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      filter.submit({
        type: 'file_edit',
        file: '/project/node_modules/lodash/index.js',
      });

      filter.flush();
      expect(emitted.length).toBe(0);
      expect(filter.getStats().filtered).toBe(1);
    });

    test('ignores .git directory', () => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      filter.submit({
        type: 'file_edit',
        file: '/project/.git/objects/abc123',
      });

      filter.flush();
      expect(emitted.length).toBe(0);
    });

    test('ignores build artifacts', () => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      filter.submit({ type: 'file_edit', file: '/project/dist/bundle.js' });
      filter.submit({ type: 'file_edit', file: '/project/build/app.js' });
      filter.submit({ type: 'file_edit', file: '/project/.next/cache/data' });

      filter.flush();
      expect(emitted.length).toBe(0);
      expect(filter.getStats().filtered).toBe(3);
    });

    test('ignores temp files', () => {
      expect(shouldIgnoreFile('/project/file.tmp')).toBe(true);
      expect(shouldIgnoreFile('/project/file.swp')).toBe(true);
      expect(shouldIgnoreFile('/project/file~')).toBe(true);
    });

    test('ignores lock files', () => {
      expect(shouldIgnoreFile('/project/package-lock.json')).toBe(true);
      expect(shouldIgnoreFile('/project/yarn.lock')).toBe(true);
      expect(shouldIgnoreFile('/project/pnpm-lock.yaml')).toBe(true);
    });

    test('passes normal source files', () => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      filter.submit({ type: 'file_edit', file: '/project/src/index.ts' });
      filter.flush();

      expect(emitted.length).toBe(1);
      expect(filter.getStats().passed).toBe(1);
    });
  });

  describe('Debouncing', () => {
    test('debounces rapid file edits', (done) => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      // Submit 5 rapid edits to same file
      for (let i = 0; i < 5; i++) {
        filter.submit({
          type: 'file_edit',
          file: '/project/src/app.ts',
          data: { gist: `Edit ${i}` },
        });
      }

      // Should only emit one event after debounce delay
      setTimeout(() => {
        expect(emitted.length).toBe(1);
        expect(filter.getStats().debounced).toBe(4);
        done();
      }, 600);
    });

    test('debounces by file - different files get separate events', (done) => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      filter.submit({ type: 'file_edit', file: '/project/src/a.ts' });
      filter.submit({ type: 'file_edit', file: '/project/src/b.ts' });
      filter.submit({ type: 'file_edit', file: '/project/src/c.ts' });

      setTimeout(() => {
        expect(emitted.length).toBe(3);
        done();
      }, 600);
    });
  });

  describe('Deduplication', () => {
    test('deduplicates identical events within window', () => {
      // Use filter without batching for simpler test
      const noBatchFilter = new EdgeFilter({
        enableBatching: false,
        debounceDelay: 0,
      });

      const emitted: FilterableEvent[] = [];
      noBatchFilter.on('event', (e) => emitted.push(e));

      // Submit same event twice quickly
      noBatchFilter.submit({ type: 'focus', file: '/project/src/app.ts' });
      noBatchFilter.submit({ type: 'focus', file: '/project/src/app.ts' });

      expect(emitted.length).toBe(1);
      expect(noBatchFilter.getStats().deduplicated).toBe(1);

      noBatchFilter.destroy();
    });
  });

  describe('Rate Limiting', () => {
    test('limits events per second', () => {
      const rateLimitFilter = new EdgeFilter({
        maxEventsPerSecond: 5,
        enableBatching: false,
        enableSmartFilter: false,
        debounceDelay: 0,
      });

      const emitted: FilterableEvent[] = [];
      rateLimitFilter.on('event', (e) => emitted.push(e));

      // Submit 10 events rapidly
      for (let i = 0; i < 10; i++) {
        rateLimitFilter.submit({
          type: 'terminal',
          data: { command: `cmd${i}` },
        });
      }

      // Should only pass 5
      expect(rateLimitFilter.getStats().rateLimited).toBe(5);

      rateLimitFilter.destroy();
    });
  });

  describe('Batching', () => {
    test('batches multiple events', (done) => {
      const batchFilter = new EdgeFilter({
        enableBatching: true,
        batchWindow: 50,
        maxBatchSize: 10,
        enableSmartFilter: false,
        debounceDelay: 0,
      });

      const batches: FilterableEvent[][] = [];
      batchFilter.on('batch', (events) => batches.push(events));

      // Submit several non-debounced events
      batchFilter.submit({ type: 'terminal', data: { command: 'cmd1' } });
      batchFilter.submit({ type: 'terminal', data: { command: 'cmd2' } });
      batchFilter.submit({ type: 'terminal', data: { command: 'cmd3' } });

      setTimeout(() => {
        expect(batches.length).toBe(1);
        expect(batches[0].length).toBe(3);
        batchFilter.destroy();
        done();
      }, 100);
    });

    test('flushes batch when max size reached', () => {
      const batchFilter = new EdgeFilter({
        enableBatching: true,
        batchWindow: 10000, // Long window
        maxBatchSize: 3,
        enableSmartFilter: false,
        debounceDelay: 0,
      });

      const batches: FilterableEvent[][] = [];
      batchFilter.on('batch', (events) => batches.push(events));

      // Submit 3 events (max batch size)
      batchFilter.submit({ type: 'terminal', data: { command: 'cmd1' } });
      batchFilter.submit({ type: 'terminal', data: { command: 'cmd2' } });
      batchFilter.submit({ type: 'terminal', data: { command: 'cmd3' } });

      // Should flush immediately
      expect(batches.length).toBe(1);
      expect(batches[0].length).toBe(3);

      batchFilter.destroy();
    });
  });

  describe('Statistics', () => {
    test('tracks all statistics', () => {
      const stats = filter.getStats();

      expect(stats).toHaveProperty('received');
      expect(stats).toHaveProperty('passed');
      expect(stats).toHaveProperty('debounced');
      expect(stats).toHaveProperty('deduplicated');
      expect(stats).toHaveProperty('rateLimited');
      expect(stats).toHaveProperty('filtered');
      expect(stats).toHaveProperty('batched');
    });

    test('resetStats clears statistics', () => {
      filter.submit({ type: 'file_edit', file: '/project/node_modules/x' });
      expect(filter.getStats().received).toBe(1);

      filter.resetStats();
      expect(filter.getStats().received).toBe(0);
    });
  });

  describe('Flush', () => {
    test('flush emits all pending events', (done) => {
      const emitted: FilterableEvent[] = [];
      filter.on('event', (e) => emitted.push(e));

      // Submit debounced events
      filter.submit({ type: 'file_edit', file: '/project/src/a.ts' });
      filter.submit({ type: 'file_edit', file: '/project/src/b.ts' });

      // Flush immediately
      filter.flush();

      // Events should be emitted immediately
      expect(emitted.length).toBe(2);
      done();
    });
  });
});

describe('shouldIgnoreFile utility', () => {
  test('handles Windows paths', () => {
    expect(shouldIgnoreFile('C:\\project\\node_modules\\lodash\\index.js')).toBe(true);
    expect(shouldIgnoreFile('C:\\project\\.git\\HEAD')).toBe(true);
    expect(shouldIgnoreFile('C:\\project\\src\\app.ts')).toBe(false);
  });

  test('handles Unix paths', () => {
    expect(shouldIgnoreFile('/home/user/project/node_modules/lodash/index.js')).toBe(true);
    expect(shouldIgnoreFile('/home/user/project/.git/HEAD')).toBe(true);
    expect(shouldIgnoreFile('/home/user/project/src/app.ts')).toBe(false);
  });
});
