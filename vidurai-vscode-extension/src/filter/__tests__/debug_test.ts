import { EdgeFilter, FilterableEvent } from '../EdgeFilter';

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const filter = new EdgeFilter({
    debug: true,
    debounceDelay: 100,
    enableBatching: false,
  });

  const emitted: FilterableEvent[] = [];
  filter.on('event', (e: FilterableEvent) => {
    console.log('EVENT RECEIVED:', e.type, e.file);
    emitted.push(e);
  });

  console.log('Submitting 5 events...');
  for (let i = 0; i < 5; i++) {
    console.log('Submit event ' + (i + 1));
    filter.submit({
      type: 'file_edit',
      file: '/project/src/app.ts',
      data: { gist: 'Edit ' + i },
    });
  }

  console.log('After submit, emitted:', emitted.length);
  console.log('Stats:', JSON.stringify(filter.getStats(), null, 2));

  console.log('\nWaiting 150ms...');
  await sleep(150);

  console.log('After wait, emitted:', emitted.length);
  console.log('Stats:', JSON.stringify(filter.getStats(), null, 2));

  filter.destroy();
}

main().catch(console.error);
