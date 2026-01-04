/**
 * Gatekeeper Unit Tests
 *
 * Tests for the edge security module that sanitizes secrets
 * before data leaves the VS Code extension.
 *
 * Run: npm test -- --grep "Gatekeeper"
 */

import { Gatekeeper, sanitize, hasSecrets, SanitizeResult, SecretType } from '../Gatekeeper';

// =============================================================================
// TEST UTILITIES
// =============================================================================

function assertRedacted(result: SanitizeResult, type: SecretType, count: number = 1): void {
  if (!result.hasSecrets) {
    throw new Error(`Expected secrets to be detected, but hasSecrets is false`);
  }
  if ((result.secretCounts[type] || 0) !== count) {
    throw new Error(
      `Expected ${count} ${type} redactions, got ${result.secretCounts[type] || 0}`
    );
  }
  if (!result.sanitized.includes(`<REDACTED:${type}:`)) {
    throw new Error(`Expected sanitized output to contain <REDACTED:${type}:...>`);
  }
}

function assertNotRedacted(result: SanitizeResult, original: string): void {
  if (result.hasSecrets) {
    throw new Error(
      `Expected no secrets, but found: ${JSON.stringify(result.secretCounts)}`
    );
  }
  if (result.sanitized !== original) {
    throw new Error(`Expected original text to be unchanged`);
  }
}

// =============================================================================
// TEST CASES
// =============================================================================

describe('Gatekeeper', () => {
  let gatekeeper: Gatekeeper;

  beforeEach(() => {
    gatekeeper = new Gatekeeper();
  });

  // -------------------------------------------------------------------------
  // OpenAI Keys
  // -------------------------------------------------------------------------
  describe('OpenAI Key Detection', () => {
    test('should redact sk-proj-TESTKEY* format keys', () => {
      const input = 'OPENAI_API_KEY=sk-proj-TESTKEY';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'OPENAI_KEY');
      expect(result.sanitized).not.toContain('sk-proj-TESTKEY');
      expect(result.sanitized).toContain('<REDACTED:OPENAI_KEY:');
    });

    test('should redact classic sk-* format keys', () => {
      const input = 'key = "sk-FAKEKEY1234567890"';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'OPENAI_KEY');
    });

    test('should redact sk-svcacct-TESTKEY* format keys', () => {
      const input = 'export OPENAI_KEY=sk-svcacct-TESTKEY';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'OPENAI_KEY');
    });
  });

  // -------------------------------------------------------------------------
  // No False Positives
  // -------------------------------------------------------------------------
  describe('False Positive Prevention', () => {
    test('should NOT redact normal print statements', () => {
      const input = 'print("hello")';
      const result = gatekeeper.sanitize(input);

      assertNotRedacted(result, input);
    });

    test('should NOT redact normal variable assignments', () => {
      const input = 'const message = "Hello, World!";';
      const result = gatekeeper.sanitize(input);

      assertNotRedacted(result, input);
    });

    test('should NOT redact normal function definitions', () => {
      const input = `
function calculateSum(a: number, b: number): number {
  return a + b;
}
      `.trim();
      const result = gatekeeper.sanitize(input);

      assertNotRedacted(result, input);
    });

    test('should NOT redact short strings that look like keys', () => {
      const input = 'id = "abc123"';
      const result = gatekeeper.sanitize(input);

      assertNotRedacted(result, input);
    });

    test('should NOT redact localhost IP addresses', () => {
      const input = 'server = "127.0.0.1:8080"';
      const result = gatekeeper.sanitize(input);

      // 127.0.0.1 is explicitly excluded
      expect(result.secretCounts['IP_ADDRESS'] || 0).toBe(0);
    });

    test('should NOT redact common placeholder values', () => {
      const input = 'API_KEY=your-api-key-here';
      const result = gatekeeper.sanitize(input);

      // "your-api-key-here" has low entropy, should be skipped
      expect(result.hasSecrets).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // AWS Keys
  // -------------------------------------------------------------------------
  describe('AWS Key Detection', () => {
    test('should redact AWS Access Key IDs', () => {
      const input = 'AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'AWS_ACCESS_KEY');
    });

    test('should redact AWS keys in JSON format', () => {
      const input = '{"accessKeyId": "AKIAIOSFODNN7EXAMPLE", "region": "us-east-1"}';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'AWS_ACCESS_KEY');
      expect(result.sanitized).toContain('"region": "us-east-1"'); // Region preserved
    });
  });

  // -------------------------------------------------------------------------
  // GitHub Tokens
  // -------------------------------------------------------------------------
  describe('GitHub Token Detection', () => {
    test('should redact ghp_* format tokens', () => {
      const input = 'GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'GITHUB_TOKEN');
    });

    test('should redact github_pat_* format tokens', () => {
      const input =
        'token: github_pat_11ABCDEFGHIJKLMNOPQRST_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'GITHUB_PAT');
    });
  });

  // -------------------------------------------------------------------------
  // Private Keys
  // -------------------------------------------------------------------------
  describe('Private Key Detection', () => {
    test('should redact RSA private keys', () => {
      const input = `
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MmE2g8kv6Y5quLUj
samplekeycontenthere1234567890abcdefghijklmnopqrstuvwxyz
-----END RSA PRIVATE KEY-----
      `.trim();
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'RSA_PRIVATE_KEY');
      expect(result.sanitized).not.toContain('MIIEpAIBAAKCAQEA');
    });

    test('should redact SSH private keys', () => {
      const input = `
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAlwAAAAdzc2gtcn
-----END OPENSSH PRIVATE KEY-----
      `.trim();
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'SSH_PRIVATE_KEY');
    });

    test('should redact PGP private keys', () => {
      const input = `
-----BEGIN PGP PRIVATE KEY BLOCK-----
lQPGBGRkZ2sBCADFHvP4TH5V5S5pv5V5S5pv5V5S5pv5V5S5pv5V5S5pv5V5S5pv
-----END PGP PRIVATE KEY BLOCK-----
      `.trim();
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'PGP_PRIVATE_KEY');
    });
  });

  // -------------------------------------------------------------------------
  // Database URLs
  // -------------------------------------------------------------------------
  describe('Database URL Detection', () => {
    test('should redact PostgreSQL connection strings', () => {
      const input = 'DATABASE_URL=postgres://user:password123@db.example.com:5432/mydb';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'POSTGRES_URL');
      expect(result.sanitized).not.toContain('password123');
    });

    test('should redact MongoDB connection strings', () => {
      const input = 'MONGO_URI="mongodb+srv://admin:secretpass@cluster.mongodb.net/test"';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'MONGODB_URL');
    });

    test('should redact Redis connection strings', () => {
      const input = 'REDIS_URL=redis://:mysecretpassword@redis.example.com:6379';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'REDIS_URL');
    });
  });

  // -------------------------------------------------------------------------
  // JWT Tokens
  // -------------------------------------------------------------------------
  describe('JWT Token Detection', () => {
    test('should redact JWT tokens', () => {
      const input =
        'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'JWT_TOKEN');
      expect(result.sanitized).not.toContain('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');
    });
  });

  // -------------------------------------------------------------------------
  // Stripe Keys
  // -------------------------------------------------------------------------
  describe('Stripe Key Detection', () => {
    test('should redact Stripe publishable keys', () => {
      const input = 'STRIPE_PK=pk_live_51234567890abcdefghijklmn';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'STRIPE_KEY');
    });

    test('should redact Stripe secret keys', () => {
      const input = 'stripe.api_key = "sk_test_51234567890abcdefghijklmn"';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'STRIPE_SECRET');
    });
  });

  // -------------------------------------------------------------------------
  // Anthropic Keys
  // -------------------------------------------------------------------------
  describe('Anthropic Key Detection', () => {
    test('should redact sk-ant-* format keys', () => {
      const input = 'ANTHROPIC_API_KEY=sk-ant-TESTKEY';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'ANTHROPIC_KEY');
    });
  });

  // -------------------------------------------------------------------------
  // Communication Platforms
  // -------------------------------------------------------------------------
  describe('Communication Platform Token Detection', () => {
    test('should redact Slack tokens', () => {
      const input = 'SLACK_TOKEN=xoxb-FAKE-TEST-TOKEN-NOT-REAL';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'SLACK_TOKEN');
    });

    test('should redact Slack webhooks', () => {
      const input = 'webhook: https://hooks.slack.com/services/TFAKE/BFAKE/FAKE_WEBHOOK_TEST';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'SLACK_WEBHOOK');
    });

    test('should redact Discord webhooks', () => {
      const input = 'https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'DISCORD_WEBHOOK');
    });
  });

  // -------------------------------------------------------------------------
  // PII Detection
  // -------------------------------------------------------------------------
  describe('PII Detection', () => {
    test('should redact email addresses', () => {
      const input = 'Contact: john.doe@example.com for support';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'EMAIL_ADDRESS');
    });

    test('should redact US phone numbers', () => {
      const input = 'Call us at (555) 123-4567 or +1-555-987-6543';
      const result = gatekeeper.sanitize(input);

      expect(result.secretCounts['PHONE_NUMBER']).toBeGreaterThanOrEqual(1);
    });

    test('should redact SSN', () => {
      const input = 'SSN: 123-45-6789';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'SSN');
    });

    test('should redact external IP addresses', () => {
      const input = 'Server IP: 192.168.1.100';
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'IP_ADDRESS');
    });
  });

  // -------------------------------------------------------------------------
  // Entropy Optimization
  // -------------------------------------------------------------------------
  describe('Entropy Optimization', () => {
    test('should calculate entropy correctly for random strings', () => {
      // Random base64-like string should have high entropy
      const randomString = 'aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5zA7bC9';
      const entropy = gatekeeper.calculateEntropy(randomString);

      expect(entropy).toBeGreaterThan(4.0);
    });

    test('should calculate entropy correctly for repetitive strings', () => {
      // Repetitive string should have low entropy
      const repetitive = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
      const entropy = gatekeeper.calculateEntropy(repetitive);

      expect(entropy).toBeLessThan(1.0);
    });

    test('should calculate entropy correctly for English text', () => {
      const english = 'The quick brown fox jumps over the lazy dog';
      const entropy = gatekeeper.calculateEntropy(english);

      // English text typically has entropy around 4.0-5.0
      expect(entropy).toBeGreaterThan(3.5);
      expect(entropy).toBeLessThan(5.5);
    });

    test('should skip heavy regex for large low-entropy files', () => {
      // Generate a large low-entropy string (repeated pattern)
      const lowEntropyContent = 'hello world '.repeat(10000); // ~120KB
      const result = gatekeeper.sanitize(lowEntropyContent);

      expect(result.entropySkipped).toBe(true);
      expect(result.hasSecrets).toBe(false);
    });

    test('should still detect critical secrets in large low-entropy files', () => {
      // Large file with a critical secret embedded
      const content =
        'hello world '.repeat(5000) +
        'AKIAIOSFODNN7EXAMPLE' +
        'hello world '.repeat(5000);

      const result = gatekeeper.sanitize(content);

      // Even with entropy skip, critical patterns should be detected
      expect(result.entropySkipped).toBe(true);
      assertRedacted(result, 'AWS_ACCESS_KEY');
    });
  });

  // -------------------------------------------------------------------------
  // Multiple Secrets
  // -------------------------------------------------------------------------
  describe('Multiple Secret Detection', () => {
    test('should detect multiple different secret types', () => {
      const input = `
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        OPENAI_KEY=sk-proj-TESTKEY
        GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
      `;
      const result = gatekeeper.sanitize(input);

      expect(result.totalRedactions).toBe(3);
      expect(result.secretCounts['AWS_ACCESS_KEY']).toBe(1);
      expect(result.secretCounts['OPENAI_KEY']).toBe(1);
      expect(result.secretCounts['GITHUB_TOKEN']).toBe(1);
    });

    test('should detect multiple instances of same secret type', () => {
      const input = `
        PRIMARY_KEY=AKIAIOSFODNN7EXAMPLE
        BACKUP_KEY=AKIAIOSFODNN7BACKUP1
      `;
      const result = gatekeeper.sanitize(input);

      expect(result.secretCounts['AWS_ACCESS_KEY']).toBe(2);
    });
  });

  // -------------------------------------------------------------------------
  // Hash Consistency
  // -------------------------------------------------------------------------
  describe('Hash Consistency', () => {
    test('should produce consistent hashes for same secret', () => {
      const secret = 'sk-proj-TESTKEY';
      const result1 = gatekeeper.sanitize(`KEY=${secret}`);
      const result2 = gatekeeper.sanitize(`API_KEY=${secret}`);

      // Extract hash from redaction tokens
      const hashPattern = /<REDACTED:OPENAI_KEY:([a-f0-9]+)>/;
      const hash1 = result1.sanitized.match(hashPattern)?.[1];
      const hash2 = result2.sanitized.match(hashPattern)?.[1];

      expect(hash1).toBe(hash2);
    });

    test('should produce different hashes for different secrets', () => {
      const result1 = gatekeeper.sanitize('KEY=sk-proj-TESTKEY');
      const result2 = gatekeeper.sanitize('KEY=sk-proj-TESTKEY');

      const hashPattern = /<REDACTED:OPENAI_KEY:([a-f0-9]+)>/;
      const hash1 = result1.sanitized.match(hashPattern)?.[1];
      const hash2 = result2.sanitized.match(hashPattern)?.[1];

      expect(hash1).not.toBe(hash2);
    });
  });

  // -------------------------------------------------------------------------
  // Scan Function
  // -------------------------------------------------------------------------
  describe('Scan Function', () => {
    test('should return detailed findings with positions', () => {
      const input = 'API_KEY=sk-proj-TESTKEY';
      const findings = gatekeeper.scan(input);

      expect(findings.length).toBe(1);
      expect(findings[0].type).toBe('OPENAI_KEY');
      expect(findings[0].start).toBeGreaterThan(0);
      expect(findings[0].end).toBeGreaterThan(findings[0].start);
      expect(findings[0].preview).toMatch(/sk-p\.\..def/);
    });
  });

  // -------------------------------------------------------------------------
  // Convenience Functions
  // -------------------------------------------------------------------------
  describe('Convenience Functions', () => {
    test('sanitize() function should work', () => {
      const result = sanitize('KEY=sk-proj-TESTKEY');
      expect(result.hasSecrets).toBe(true);
    });

    test('hasSecrets() function should work', () => {
      expect(hasSecrets('sk-proj-TESTKEY')).toBe(true);
      expect(hasSecrets('print("hello")')).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Edge Cases
  // -------------------------------------------------------------------------
  describe('Edge Cases', () => {
    test('should handle empty string', () => {
      const result = gatekeeper.sanitize('');
      expect(result.hasSecrets).toBe(false);
      expect(result.sanitized).toBe('');
    });

    test('should handle null-like inputs gracefully', () => {
      // @ts-ignore - Testing runtime behavior
      const result = gatekeeper.sanitize(null as any);
      expect(result.hasSecrets).toBe(false);
    });

    test('should handle very short strings', () => {
      const result = gatekeeper.sanitize('hi');
      expect(result.hasSecrets).toBe(false);
      expect(result.sanitized).toBe('hi');
    });

    test('should handle unicode content', () => {
      const input = 'API_KEY=sk-proj-TESTKEY' + '1234567890abcdef' + ' // API key';
      const result = gatekeeper.sanitize(input);
      assertRedacted(result, 'OPENAI_KEY');
    });

    test('should handle multiline content', () => {
      const input = `
# Configuration file
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_REGION=us-east-1
DEBUG=true
      `;
      const result = gatekeeper.sanitize(input);

      assertRedacted(result, 'AWS_ACCESS_KEY');
      expect(result.sanitized).toContain('AWS_REGION=us-east-1');
      expect(result.sanitized).toContain('DEBUG=true');
    });
  });
});

// =============================================================================
// MANUAL TEST RUNNER (for environments without Jest)
// =============================================================================

/**
 * Simple test runner for manual verification
 * Run with: npx ts-node Gatekeeper.test.ts
 */
export function runManualTests(): void {
  console.log('Running Gatekeeper Manual Tests...\n');

  const gatekeeper = new Gatekeeper();
  let passed = 0;
  let failed = 0;

  // Test 1: OpenAI Key Redaction
  try {
    const result = gatekeeper.sanitize('sk-proj-TESTKEY');
    if (result.hasSecrets && result.sanitized.includes('<REDACTED:OPENAI_KEY:')) {
      console.log('PASS: OpenAI key redaction');
      passed++;
    } else {
      throw new Error('OpenAI key not redacted');
    }
  } catch (e: any) {
    console.log('FAIL: OpenAI key redaction -', e.message);
    failed++;
  }

  // Test 2: No False Positive
  try {
    const result = gatekeeper.sanitize('print("hello")');
    if (!result.hasSecrets && result.sanitized === 'print("hello")') {
      console.log('PASS: No false positive on print statement');
      passed++;
    } else {
      throw new Error('False positive detected');
    }
  } catch (e: any) {
    console.log('FAIL: No false positive -', e.message);
    failed++;
  }

  // Test 3: AWS Key Detection
  try {
    const result = gatekeeper.sanitize('AKIAIOSFODNN7EXAMPLE');
    if (result.hasSecrets && result.secretCounts['AWS_ACCESS_KEY'] === 1) {
      console.log('PASS: AWS key detection');
      passed++;
    } else {
      throw new Error('AWS key not detected');
    }
  } catch (e: any) {
    console.log('FAIL: AWS key detection -', e.message);
    failed++;
  }

  // Test 4: Private Key Detection
  try {
    const privateKey = '-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----';
    const result = gatekeeper.sanitize(privateKey);
    if (result.hasSecrets && result.secretCounts['RSA_PRIVATE_KEY'] === 1) {
      console.log('PASS: RSA private key detection');
      passed++;
    } else {
      throw new Error('RSA private key not detected');
    }
  } catch (e: any) {
    console.log('FAIL: RSA private key detection -', e.message);
    failed++;
  }

  // Test 5: Hash Determinism
  try {
    const secret = 'sk-proj-TESTKEY';
    const result1 = gatekeeper.sanitize(secret);
    const result2 = gatekeeper.sanitize(secret);
    if (result1.sanitized === result2.sanitized) {
      console.log('PASS: Hash determinism');
      passed++;
    } else {
      throw new Error('Hashes not deterministic');
    }
  } catch (e: any) {
    console.log('FAIL: Hash determinism -', e.message);
    failed++;
  }

  console.log(`\nResults: ${passed} passed, ${failed} failed`);
}

// Run manual tests if executed directly
if (require.main === module) {
  runManualTests();
}
