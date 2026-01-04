/**
 * Manual IPC Client Test
 *
 * Tests the IPC client connection to the daemon.
 *
 * Usage:
 *   1. Start the daemon: cd vidurai-daemon && python3 daemon.py
 *   2. Run this test: npx ts-node src/ipc/__tests__/manual_test.ts
 */

import { IPCClient } from '../Client';

async function main() {
  console.log('='.repeat(60));
  console.log('IPC CLIENT MANUAL TEST (v2.1 with Circuit Breaker)');
  console.log('='.repeat(60));
  console.log('');

  const client = new IPCClient({ debug: true });

  console.log(`Session ID: ${client.getSessionId()}`);
  console.log(`Pipe Path: ${client.getPipePath()}`);
  console.log(`Buffer Path: ${client.getBufferPath()}`);
  console.log(`Has Buffered Events: ${client.hasBufferedEvents()}`);
  console.log('');

  // Event handlers
  client.on('connected', () => {
    console.log('EVENT: connected');
  });

  client.on('disconnected', (error) => {
    console.log('EVENT: disconnected', error?.message || '');
  });

  client.on('error', (error) => {
    console.log('EVENT: error', error.message);
  });

  client.on('heartbeat', (ts) => {
    console.log(`EVENT: heartbeat at ${new Date(ts).toISOString()}`);
  });

  client.on('stateChange', (state) => {
    console.log(`EVENT: state changed to ${state}`);
  });

  client.on('bufferDrained', (stats) => {
    console.log(`EVENT: buffer drained - ${stats.count} events, ${stats.errors} errors`);
  });

  try {
    // Test 1: Connect
    console.log('TEST 1: Connecting...');
    await client.connect();
    console.log('PASS: Connected successfully');
    console.log('');

    // Test 2: Ping
    console.log('TEST 2: Sending ping...');
    const pongResult = await client.ping();
    if (pongResult) {
      console.log('PASS: Received pong');
    } else {
      console.log('FAIL: No pong received');
    }
    console.log('');

    // Test 3: Send file_edit event
    console.log('TEST 3: Sending file_edit event...');
    const editResponse = await client.send('file_edit', {
      file: '/test/example.ts',
      gist: 'Updated test file',
      change: 'save',
      lang: 'typescript',
    });
    if (editResponse.ok) {
      console.log('PASS: file_edit acknowledged');
    } else {
      console.log('FAIL: file_edit failed:', editResponse.error);
    }
    console.log('');

    // Test 4: Request stats
    console.log('TEST 4: Requesting stats...');
    const statsResponse = await client.send('stats');
    if (statsResponse.ok && statsResponse.data) {
      console.log('PASS: Stats received:');
      console.log('  - Projects:', statsResponse.data.projects);
      console.log('  - Files:', statsResponse.data.files);
      console.log('  - Changes:', statsResponse.data.changes);
    } else {
      console.log('FAIL: Stats failed:', statsResponse.error);
    }
    console.log('');

    // Test 5: Request context
    console.log('TEST 5: Requesting context...');
    const contextResponse = await client.send('context', {
      query: 'What was I working on?',
      maxTokens: 1000,
    });
    if (contextResponse.ok && contextResponse.data) {
      console.log('PASS: Context received:');
      console.log('  - Length:', contextResponse.data.context?.length || 0);
      console.log('  - Count:', contextResponse.data.count);
    } else {
      console.log('FAIL: Context failed:', contextResponse.error);
    }
    console.log('');

    // Test 6: Wait for heartbeat
    console.log('TEST 6: Waiting for heartbeat (up to 10s)...');
    const heartbeatPromise = new Promise<boolean>((resolve) => {
      const timeout = setTimeout(() => resolve(false), 10000);
      client.once('heartbeat', () => {
        clearTimeout(timeout);
        resolve(true);
      });
    });

    const gotHeartbeat = await heartbeatPromise;
    if (gotHeartbeat) {
      console.log('PASS: Heartbeat received');
    } else {
      console.log('FAIL: No heartbeat within 10s');
    }
    console.log('');

    // Test 7: Drain orphaned buffers
    console.log('TEST 7: Draining orphaned buffers...');
    const orphanStats = await client.drainOrphanedBuffers();
    if (orphanStats.files > 0) {
      console.log(`PASS: Drained ${orphanStats.events} events from ${orphanStats.files} orphaned file(s)`);
    } else {
      console.log('INFO: No orphaned buffers found (expected if clean startup)');
    }
    console.log('');

    // Summary
    console.log('='.repeat(60));
    console.log('TESTS COMPLETE');
    console.log('='.repeat(60));

  } catch (error: any) {
    console.error('ERROR:', error.message);
    console.log('');
    console.log('Make sure the daemon is running:');
    console.log('  cd vidurai-daemon && python3 daemon.py');
  } finally {
    console.log('');
    console.log('Disconnecting...');
    client.disconnect();
    console.log('Done.');
  }
}

main().catch(console.error);
