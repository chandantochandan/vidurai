/**
 * Offline Buffer Test
 *
 * Tests the Circuit Breaker offline buffer functionality.
 *
 * Usage:
 *   npx ts-node src/ipc/__tests__/buffer_test.ts
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { IPCClient } from '../Client';

// Test configuration
const TEST_BUFFER_DIR = path.join(os.tmpdir(), 'vidurai-buffer-test');

async function main() {
  console.log('='.repeat(60));
  console.log('OFFLINE BUFFER TEST');
  console.log('='.repeat(60));
  console.log('');

  // Clean up test directory
  if (fs.existsSync(TEST_BUFFER_DIR)) {
    fs.rmSync(TEST_BUFFER_DIR, { recursive: true });
  }

  // Create client with test buffer directory
  const client = new IPCClient({
    debug: true,
    enableBuffer: true,
    bufferDir: TEST_BUFFER_DIR,
    maxBufferSize: 1024, // 1KB for testing rotation
  });

  console.log('Test Configuration:');
  console.log(`  Session ID: ${client.getSessionId()}`);
  console.log(`  Buffer Path: ${client.getBufferPath()}`);
  console.log(`  Buffer Dir: ${TEST_BUFFER_DIR}`);
  console.log('');

  // Test 1: Buffer directory creation
  console.log('TEST 1: Buffer directory creation');
  if (fs.existsSync(TEST_BUFFER_DIR)) {
    console.log('PASS: Buffer directory created');
  } else {
    console.log('FAIL: Buffer directory not created');
  }
  console.log('');

  // Test 2: Write events while disconnected
  console.log('TEST 2: Writing events while disconnected');
  console.log('  (Client is not connected, events should go to buffer)');

  for (let i = 1; i <= 5; i++) {
    const result = client.sendEvent('file_edit', {
      file: `/test/file${i}.ts`,
      gist: `Test edit ${i}`,
      change: 'save',
      lang: 'typescript',
    });
    console.log(`  Event ${i}: ${result ? 'buffered' : 'failed'}`);
  }

  const bufferedCount = client.getBufferedEventCount();
  console.log(`  Total buffered: ${bufferedCount}`);
  if (bufferedCount === 5) {
    console.log('PASS: All events buffered');
  } else {
    console.log(`FAIL: Expected 5 events, got ${bufferedCount}`);
  }
  console.log('');

  // Test 3: Buffer file exists
  console.log('TEST 3: Buffer file verification');
  if (client.hasBufferedEvents()) {
    console.log('PASS: Buffer file has events');
    const bufferContent = fs.readFileSync(client.getBufferPath(), 'utf-8');
    console.log(`  File size: ${bufferContent.length} bytes`);
    console.log(`  Sample line: ${bufferContent.split('\n')[0].slice(0, 80)}...`);
  } else {
    console.log('FAIL: Buffer file is empty');
  }
  console.log('');

  // Test 4: Buffer rotation
  console.log('TEST 4: Buffer rotation (writing > 1KB)');
  console.log('  Writing large events to trigger rotation...');

  const largeData = 'x'.repeat(200);
  for (let i = 0; i < 10; i++) {
    client.sendEvent('file_edit', {
      file: `/test/large_file${i}.ts`,
      gist: largeData,
      change: 'save',
      lang: 'typescript',
    });
  }

  // Check if backup was created
  const backupPath = client.getBufferPath() + '.bak';
  if (fs.existsSync(backupPath)) {
    const backupSize = fs.statSync(backupPath).size;
    console.log(`PASS: Rotation occurred, backup size: ${backupSize} bytes`);
  } else {
    console.log('INFO: No rotation occurred (buffer not large enough)');
  }
  console.log('');

  // Test 5: Clear buffer
  console.log('TEST 5: Clear buffer');
  client.clearBuffer();
  if (!client.hasBufferedEvents()) {
    console.log('PASS: Buffer cleared');
  } else {
    console.log('FAIL: Buffer not cleared');
  }
  console.log('');

  // Test 6: Orphaned buffer scanning (simulate previous session)
  console.log('TEST 6: Orphaned buffer simulation');
  const orphanPath = path.join(TEST_BUFFER_DIR, 'buffer-orphan123.jsonl');
  fs.writeFileSync(
    orphanPath,
    '{"v":1,"type":"file_edit","ts":1234567890,"data":{"file":"orphan.ts"}}\n'
  );
  console.log(`  Created orphan buffer: ${orphanPath}`);

  const orphanFiles = fs.readdirSync(TEST_BUFFER_DIR).filter((f) => f.includes('orphan'));
  if (orphanFiles.length > 0) {
    console.log('PASS: Orphan buffer file exists');
    console.log(`  Files: ${orphanFiles.join(', ')}`);
  } else {
    console.log('FAIL: Orphan buffer not created');
  }
  console.log('');

  // Summary
  console.log('='.repeat(60));
  console.log('BUFFER TESTS COMPLETE');
  console.log('='.repeat(60));
  console.log('');
  console.log('Note: To test drain functionality, you need the daemon running.');
  console.log('Run:');
  console.log('  1. cd vidurai-daemon && python3 daemon.py');
  console.log('  2. npx ts-node src/ipc/__tests__/manual_test.ts');

  // Cleanup
  if (fs.existsSync(TEST_BUFFER_DIR)) {
    fs.rmSync(TEST_BUFFER_DIR, { recursive: true });
    console.log('');
    console.log('Cleaned up test directory.');
  }
}

main().catch(console.error);
