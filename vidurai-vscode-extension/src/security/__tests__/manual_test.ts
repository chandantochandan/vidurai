/**
 * Manual Test Runner for Gatekeeper
 *
 * Run: npx ts-node src/security/__tests__/manual_test.ts
 */

import { Gatekeeper, sanitize, hasSecrets } from '../Gatekeeper';

console.log('='.repeat(60));
console.log('GATEKEEPER MANUAL TESTS');
console.log('='.repeat(60));
console.log('');

const gatekeeper = new Gatekeeper();
let passed = 0;
let failed = 0;

function test(name: string, fn: () => boolean): void {
  try {
    if (fn()) {
      console.log(`PASS: ${name}`);
      passed++;
    } else {
      console.log(`FAIL: ${name}`);
      failed++;
    }
  } catch (e: any) {
    console.log(`FAIL: ${name} - ${e.message}`);
    failed++;
  }
}

// -------------------------------------------------------------------------
// Test 1: OpenAI Key Redaction (CRITICAL TEST FROM SPEC)
// -------------------------------------------------------------------------
test('OpenAI sk-proj-* key redaction', () => {
  const result = gatekeeper.sanitize('sk-proj-1234567890abcdefghijklmnop');
  return result.hasSecrets &&
    result.sanitized.includes('<REDACTED:OPENAI_KEY:') &&
    !result.sanitized.includes('sk-proj-');
});

// -------------------------------------------------------------------------
// Test 2: No False Positive on print("hello") (CRITICAL TEST FROM SPEC)
// -------------------------------------------------------------------------
test('No false positive on print("hello")', () => {
  const input = 'print("hello")';
  const result = gatekeeper.sanitize(input);
  return !result.hasSecrets && result.sanitized === input;
});

// -------------------------------------------------------------------------
// Test 3: AWS Key Detection
// -------------------------------------------------------------------------
test('AWS Access Key detection', () => {
  const result = gatekeeper.sanitize('AKIAIOSFODNN7EXAMPLE');
  return result.hasSecrets && result.secretCounts['AWS_ACCESS_KEY'] === 1;
});

// -------------------------------------------------------------------------
// Test 4: Private Key Detection
// -------------------------------------------------------------------------
test('RSA private key detection', () => {
  const privateKey = '-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----';
  const result = gatekeeper.sanitize(privateKey);
  return result.hasSecrets && result.secretCounts['RSA_PRIVATE_KEY'] === 1;
});

// -------------------------------------------------------------------------
// Test 5: GitHub Token Detection
// -------------------------------------------------------------------------
test('GitHub token (ghp_*) detection', () => {
  const result = gatekeeper.sanitize('ghp_1234567890abcdefghijklmnopqrstuvwxyz');
  return result.hasSecrets && result.secretCounts['GITHUB_TOKEN'] === 1;
});

// -------------------------------------------------------------------------
// Test 6: JWT Token Detection
// -------------------------------------------------------------------------
test('JWT token detection', () => {
  const jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U';
  const result = gatekeeper.sanitize(jwt);
  return result.hasSecrets && result.secretCounts['JWT_TOKEN'] === 1;
});

// -------------------------------------------------------------------------
// Test 7: Stripe Key Detection
// -------------------------------------------------------------------------
test('Stripe secret key detection', () => {
  const result = gatekeeper.sanitize('sk_test_51234567890abcdefghijklmn');
  return result.hasSecrets && result.secretCounts['STRIPE_SECRET'] === 1;
});

// -------------------------------------------------------------------------
// Test 8: Database URL Detection
// -------------------------------------------------------------------------
test('PostgreSQL URL detection', () => {
  const result = gatekeeper.sanitize('postgres://user:password123@db.example.com:5432/mydb');
  return result.hasSecrets && result.secretCounts['POSTGRES_URL'] === 1;
});

// -------------------------------------------------------------------------
// Test 9: Hash Determinism
// -------------------------------------------------------------------------
test('Hash is deterministic for same secret', () => {
  const secret = 'sk-proj-hashtest1234567890abcdefghij';
  const result1 = gatekeeper.sanitize(secret);
  const result2 = gatekeeper.sanitize(secret);
  return result1.sanitized === result2.sanitized;
});

// -------------------------------------------------------------------------
// Test 10: Normal Code Not Affected
// -------------------------------------------------------------------------
test('Normal function definition unchanged', () => {
  const code = `function calculateSum(a, b) { return a + b; }`;
  const result = gatekeeper.sanitize(code);
  return !result.hasSecrets && result.sanitized === code;
});

// -------------------------------------------------------------------------
// Test 11: Multiple Secrets Detection
// -------------------------------------------------------------------------
test('Multiple different secrets detected', () => {
  const input = `
    AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
    OPENAI_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz
  `;
  const result = gatekeeper.sanitize(input);
  return result.totalRedactions >= 2;
});

// -------------------------------------------------------------------------
// Test 12: Entropy Calculation
// -------------------------------------------------------------------------
test('High entropy for random strings', () => {
  const random = 'aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5zA7bC9dE1fG3';
  const entropy = gatekeeper.calculateEntropy(random);
  return entropy > 4.0;
});

test('Low entropy for repetitive strings', () => {
  const repetitive = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
  const entropy = gatekeeper.calculateEntropy(repetitive);
  return entropy < 1.0;
});

// -------------------------------------------------------------------------
// Test 13: Convenience Functions
// -------------------------------------------------------------------------
test('sanitize() convenience function works', () => {
  const result = sanitize('sk-proj-conveniencetest12345678');
  return result.hasSecrets;
});

test('hasSecrets() convenience function works', () => {
  return hasSecrets('sk-proj-hassecretstest123456789') &&
    !hasSecrets('print("hello")');
});

// -------------------------------------------------------------------------
// Test 14: Edge Cases
// -------------------------------------------------------------------------
test('Empty string handled', () => {
  const result = gatekeeper.sanitize('');
  return !result.hasSecrets && result.sanitized === '';
});

test('Very short string handled', () => {
  const result = gatekeeper.sanitize('hi');
  return !result.hasSecrets && result.sanitized === 'hi';
});

// -------------------------------------------------------------------------
// Summary
// -------------------------------------------------------------------------
console.log('');
console.log('='.repeat(60));
console.log(`RESULTS: ${passed} passed, ${failed} failed`);
console.log('='.repeat(60));

if (failed > 0) {
  process.exit(1);
}
