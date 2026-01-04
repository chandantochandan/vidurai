/**
 * Gatekeeper - Edge Security Module
 *
 * Sanitizes content before it leaves the VS Code extension.
 * Detects and redacts PII, API keys, secrets, and sensitive data.
 *
 * Philosophy: "What leaves the editor should be safe to log."
 *
 * @module security/Gatekeeper
 * @version 2.1.0
 */

import * as crypto from 'crypto';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Types of secrets that can be detected
 */
export type SecretType =
  | 'AWS_ACCESS_KEY'
  | 'AWS_SECRET_KEY'
  | 'OPENAI_KEY'
  | 'ANTHROPIC_KEY'
  | 'GITHUB_TOKEN'
  | 'GITHUB_PAT'
  | 'GITLAB_TOKEN'
  | 'STRIPE_KEY'
  | 'STRIPE_SECRET'
  | 'SLACK_TOKEN'
  | 'SLACK_WEBHOOK'
  | 'DISCORD_TOKEN'
  | 'DISCORD_WEBHOOK'
  | 'TWILIO_SID'
  | 'TWILIO_TOKEN'
  | 'SENDGRID_KEY'
  | 'MAILGUN_KEY'
  | 'JWT_TOKEN'
  | 'BEARER_TOKEN'
  | 'BASIC_AUTH'
  | 'PRIVATE_KEY'
  | 'RSA_PRIVATE_KEY'
  | 'SSH_PRIVATE_KEY'
  | 'PGP_PRIVATE_KEY'
  | 'CERTIFICATE'
  | 'DATABASE_URL'
  | 'POSTGRES_URL'
  | 'MYSQL_URL'
  | 'MONGODB_URL'
  | 'REDIS_URL'
  | 'GENERIC_SECRET'
  | 'GENERIC_API_KEY'
  | 'GENERIC_PASSWORD'
  | 'IP_ADDRESS'
  | 'EMAIL_ADDRESS'
  | 'PHONE_NUMBER'
  | 'SSN'
  | 'CREDIT_CARD';

/**
 * Result of a sanitization operation
 */
export interface SanitizeResult {
  /** Sanitized text with secrets redacted */
  sanitized: string;
  /** Whether any secrets were found */
  hasSecrets: boolean;
  /** Count of secrets found by type */
  secretCounts: Partial<Record<SecretType, number>>;
  /** Total number of redactions made */
  totalRedactions: number;
  /** Whether entropy check was skipped (for large files) */
  entropySkipped: boolean;
}

/**
 * Secret pattern definition
 */
interface SecretPattern {
  type: SecretType;
  pattern: RegExp;
  /** Minimum entropy required for this pattern (0 = always match) */
  minEntropy?: number;
}

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Maximum file size (in bytes) before using entropy-first strategy
 * Files larger than this will skip heavy regex if entropy is low
 */
const LARGE_FILE_THRESHOLD = 100 * 1024; // 100KB

/**
 * Entropy threshold for standard English text
 * Text with entropy below this is unlikely to contain secrets
 */
const LOW_ENTROPY_THRESHOLD = 3.5;

/**
 * Sample size for entropy calculation on large files
 */
const ENTROPY_SAMPLE_SIZE = 8192;

// =============================================================================
// SECRET PATTERNS
// =============================================================================

/**
 * Comprehensive list of secret detection patterns
 * Ordered by specificity (most specific first)
 */
const SECRET_PATTERNS: SecretPattern[] = [
  // -------------------------------------------------------------------------
  // Cloud Provider Keys
  // -------------------------------------------------------------------------
  {
    type: 'AWS_ACCESS_KEY',
    pattern: /\b(AKIA[0-9A-Z]{16})\b/g,
  },
  {
    type: 'AWS_SECRET_KEY',
    pattern: /\b([A-Za-z0-9/+=]{40})(?=\s|"|'|$)/g,
    minEntropy: 4.0, // High entropy required
  },

  // -------------------------------------------------------------------------
  // AI Platform Keys
  // -------------------------------------------------------------------------
  {
    type: 'OPENAI_KEY',
    pattern: /\b(sk-[A-Za-z0-9]{20,}T3BlbkFJ[A-Za-z0-9]{20,})\b/g,
  },
  {
    type: 'OPENAI_KEY',
    // Newer format: sk-proj-*, sk-svcacct-*, etc.
    pattern: /\b(sk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,})\b/g,
  },
  {
    type: 'ANTHROPIC_KEY',
    pattern: /\b(sk-ant-[A-Za-z0-9_-]{20,})\b/g,
  },

  // -------------------------------------------------------------------------
  // Version Control Tokens
  // -------------------------------------------------------------------------
  {
    type: 'GITHUB_TOKEN',
    pattern: /\b(ghp_[A-Za-z0-9]{36,})\b/g,
  },
  {
    type: 'GITHUB_PAT',
    pattern: /\b(github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59})\b/g,
  },
  {
    type: 'GITLAB_TOKEN',
    pattern: /\b(glpat-[A-Za-z0-9_-]{20,})\b/g,
  },

  // -------------------------------------------------------------------------
  // Payment & Financial
  // -------------------------------------------------------------------------
  {
    type: 'STRIPE_KEY',
    pattern: /\b(pk_(?:live|test)_[A-Za-z0-9]{24,})\b/g,
  },
  {
    type: 'STRIPE_SECRET',
    pattern: /\b(sk_(?:live|test)_[A-Za-z0-9]{24,})\b/g,
  },
  {
    type: 'CREDIT_CARD',
    // Visa, Mastercard, Amex, Discover patterns with Luhn check needed
    pattern: /\b([0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4})\b/g,
    minEntropy: 3.0,
  },

  // -------------------------------------------------------------------------
  // Communication Platforms
  // -------------------------------------------------------------------------
  {
    type: 'SLACK_TOKEN',
    pattern: /\b(xox[baprs]-[A-Za-z0-9-]{10,})\b/g,
  },
  {
    type: 'SLACK_WEBHOOK',
    pattern: /\b(https:\/\/hooks\.slack\.com\/services\/T[A-Za-z0-9]+\/B[A-Za-z0-9]+\/[A-Za-z0-9]+)\b/g,
  },
  {
    type: 'DISCORD_TOKEN',
    pattern: /\b([MN][A-Za-z0-9]{23,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,})\b/g,
  },
  {
    type: 'DISCORD_WEBHOOK',
    pattern: /\b(https:\/\/discord(?:app)?\.com\/api\/webhooks\/[0-9]+\/[A-Za-z0-9_-]+)\b/g,
  },

  // -------------------------------------------------------------------------
  // Email & SMS Services
  // -------------------------------------------------------------------------
  {
    type: 'TWILIO_SID',
    pattern: /\b(AC[A-Za-z0-9]{32})\b/g,
  },
  {
    type: 'TWILIO_TOKEN',
    pattern: /\b([A-Za-z0-9]{32})(?=\s|"|'|$)/g,
    minEntropy: 4.5,
  },
  {
    type: 'SENDGRID_KEY',
    pattern: /\b(SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43})\b/g,
  },
  {
    type: 'MAILGUN_KEY',
    pattern: /\b(key-[A-Za-z0-9]{32})\b/g,
  },

  // -------------------------------------------------------------------------
  // Authentication Tokens
  // -------------------------------------------------------------------------
  {
    type: 'JWT_TOKEN',
    pattern: /\b(eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*)\b/g,
  },
  {
    type: 'BEARER_TOKEN',
    pattern: /\bBearer\s+([A-Za-z0-9_-]{20,})\b/gi,
  },
  {
    type: 'BASIC_AUTH',
    pattern: /\bBasic\s+([A-Za-z0-9+/=]{20,})\b/gi,
  },

  // -------------------------------------------------------------------------
  // Private Keys & Certificates
  // -------------------------------------------------------------------------
  {
    type: 'RSA_PRIVATE_KEY',
    pattern: /-----BEGIN RSA PRIVATE KEY-----[\s\S]*?-----END RSA PRIVATE KEY-----/g,
  },
  {
    type: 'SSH_PRIVATE_KEY',
    pattern: /-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]*?-----END OPENSSH PRIVATE KEY-----/g,
  },
  {
    type: 'PGP_PRIVATE_KEY',
    pattern: /-----BEGIN PGP PRIVATE KEY BLOCK-----[\s\S]*?-----END PGP PRIVATE KEY BLOCK-----/g,
  },
  {
    type: 'PRIVATE_KEY',
    pattern: /-----BEGIN (?:EC |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:EC |DSA )?PRIVATE KEY-----/g,
  },
  {
    type: 'CERTIFICATE',
    pattern: /-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/g,
  },

  // -------------------------------------------------------------------------
  // Database Connection Strings
  // -------------------------------------------------------------------------
  {
    type: 'POSTGRES_URL',
    pattern: /\b(postgres(?:ql)?:\/\/[^:]+:[^@]+@[^\s"']+)\b/gi,
  },
  {
    type: 'MYSQL_URL',
    pattern: /\b(mysql:\/\/[^:]+:[^@]+@[^\s"']+)\b/gi,
  },
  {
    type: 'MONGODB_URL',
    pattern: /\b(mongodb(?:\+srv)?:\/\/[^:]+:[^@]+@[^\s"']+)\b/gi,
  },
  {
    type: 'REDIS_URL',
    pattern: /\b(redis:\/\/[^:]*:[^@]+@[^\s"']+)\b/gi,
  },
  {
    type: 'DATABASE_URL',
    pattern: /\bDATABASE_URL\s*[=:]\s*["']?([^\s"']+)["']?/gi,
  },

  // -------------------------------------------------------------------------
  // Personal Identifiable Information (PII)
  // -------------------------------------------------------------------------
  {
    type: 'EMAIL_ADDRESS',
    pattern: /\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g,
  },
  {
    type: 'PHONE_NUMBER',
    // US phone numbers
    pattern: /\b(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})\b/g,
  },
  {
    type: 'SSN',
    // US Social Security Number
    pattern: /\b([0-9]{3}-[0-9]{2}-[0-9]{4})\b/g,
  },
  {
    type: 'IP_ADDRESS',
    // IPv4 addresses (but not common ones like 127.0.0.1, 0.0.0.0)
    pattern: /\b(?!127\.0\.0\.1|0\.0\.0\.0|255\.255\.255\.255)([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\b/g,
  },

  // -------------------------------------------------------------------------
  // Generic Patterns (Last Resort - Higher False Positive Risk)
  // -------------------------------------------------------------------------
  {
    type: 'GENERIC_API_KEY',
    // api_key, apikey, api-key in various formats
    pattern: /\b(?:api[_-]?key|apikey)\s*[=:]\s*["']?([A-Za-z0-9_-]{16,})["']?/gi,
  },
  {
    type: 'GENERIC_SECRET',
    // secret, secret_key, etc.
    pattern: /\b(?:secret|secret[_-]?key)\s*[=:]\s*["']?([A-Za-z0-9_-]{16,})["']?/gi,
  },
  {
    type: 'GENERIC_PASSWORD',
    // password in config/env files
    pattern: /\b(?:password|passwd|pwd)\s*[=:]\s*["']?([^\s"']{8,})["']?/gi,
  },
];

// =============================================================================
// GATEKEEPER CLASS
// =============================================================================

/**
 * Gatekeeper - Edge Security for Vidurai
 *
 * Sanitizes content by detecting and redacting secrets before
 * data leaves the VS Code extension.
 *
 * Features:
 * - Comprehensive secret pattern detection
 * - Entropy-based optimization for large files
 * - Deterministic hashing for redaction tokens
 * - Zero false negatives policy (may have some false positives)
 *
 * @example
 * ```typescript
 * const gatekeeper = new Gatekeeper();
 * const result = gatekeeper.sanitize('API_KEY=sk-proj-abc123xyz');
 * console.log(result.sanitized);
 * // Output: 'API_KEY=<REDACTED:OPENAI_KEY:a1b2c3d4>'
 * ```
 */
export class Gatekeeper {
  private patterns: SecretPattern[];

  constructor() {
    this.patterns = SECRET_PATTERNS;
  }

  /**
   * Sanitize text by redacting detected secrets
   *
   * @param text - The text to sanitize
   * @returns SanitizeResult with sanitized text and metadata
   */
  sanitize(text: string): SanitizeResult {
    const result: SanitizeResult = {
      sanitized: text,
      hasSecrets: false,
      secretCounts: {},
      totalRedactions: 0,
      entropySkipped: false,
    };

    // Empty or very short text - nothing to sanitize
    if (!text || text.length < 10) {
      return result;
    }

    // Large file optimization: check entropy first
    if (text.length > LARGE_FILE_THRESHOLD) {
      const entropy = this.calculateEntropy(text.slice(0, ENTROPY_SAMPLE_SIZE));

      if (entropy < LOW_ENTROPY_THRESHOLD) {
        // Low entropy text (standard prose/code) - skip heavy regex
        // Still run critical patterns (private keys, explicit secrets)
        result.entropySkipped = true;
        return this.sanitizeCriticalOnly(text, result);
      }
    }

    // Full sanitization
    return this.sanitizeFull(text, result);
  }

  /**
   * Perform full sanitization with all patterns
   */
  private sanitizeFull(text: string, result: SanitizeResult): SanitizeResult {
    let sanitized = text;

    for (const pattern of this.patterns) {
      // Reset regex state (important for global patterns)
      pattern.pattern.lastIndex = 0;

      sanitized = sanitized.replace(pattern.pattern, (match, captured) => {
        // For patterns with minEntropy, verify the match has sufficient entropy
        if (pattern.minEntropy) {
          const matchEntropy = this.calculateEntropy(captured || match);
          if (matchEntropy < pattern.minEntropy) {
            return match; // Keep original - likely false positive
          }
        }

        // Update counts
        result.hasSecrets = true;
        result.totalRedactions++;
        result.secretCounts[pattern.type] = (result.secretCounts[pattern.type] || 0) + 1;

        // Generate redaction token
        return this.createRedactionToken(pattern.type, captured || match);
      });
    }

    result.sanitized = sanitized;
    return result;
  }

  /**
   * Sanitize only critical patterns (private keys, certificates)
   * Used when entropy check indicates low-risk content
   */
  private sanitizeCriticalOnly(text: string, result: SanitizeResult): SanitizeResult {
    const criticalTypes: SecretType[] = [
      'RSA_PRIVATE_KEY',
      'SSH_PRIVATE_KEY',
      'PGP_PRIVATE_KEY',
      'PRIVATE_KEY',
      'CERTIFICATE',
      'AWS_ACCESS_KEY',
      'OPENAI_KEY',
      'ANTHROPIC_KEY',
      'GITHUB_TOKEN',
      'GITHUB_PAT',
    ];

    let sanitized = text;

    for (const pattern of this.patterns) {
      if (!criticalTypes.includes(pattern.type)) {
        continue;
      }

      pattern.pattern.lastIndex = 0;

      sanitized = sanitized.replace(pattern.pattern, (match, captured) => {
        result.hasSecrets = true;
        result.totalRedactions++;
        result.secretCounts[pattern.type] = (result.secretCounts[pattern.type] || 0) + 1;

        return this.createRedactionToken(pattern.type, captured || match);
      });
    }

    result.sanitized = sanitized;
    return result;
  }

  /**
   * Calculate Shannon entropy of a string
   *
   * Entropy measures randomness/unpredictability:
   * - English text: ~4.0-5.0 bits/char
   * - Random base64: ~5.5-6.0 bits/char
   * - API keys/secrets: typically >4.5 bits/char
   *
   * @param text - Text to calculate entropy for
   * @returns Entropy in bits per character
   */
  calculateEntropy(text: string): number {
    if (!text || text.length === 0) {
      return 0;
    }

    // Count character frequencies
    const freq: Map<string, number> = new Map();
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      freq.set(char, (freq.get(char) || 0) + 1);
    }

    // Calculate entropy: -sum(p * log2(p))
    let entropy = 0;
    const len = text.length;

    // Use Array.from for compatibility
    const counts = Array.from(freq.values());
    for (let i = 0; i < counts.length; i++) {
      const p = counts[i] / len;
      entropy -= p * Math.log2(p);
    }

    return entropy;
  }

  /**
   * Create a redaction token with type and truncated hash
   *
   * Format: <REDACTED:TYPE:HASH>
   * Hash is first 8 chars of SHA-256 for deterministic identification
   *
   * @param type - Secret type
   * @param value - Original secret value
   * @returns Redaction token
   */
  private createRedactionToken(type: SecretType, value: string): string {
    const hash = crypto
      .createHash('sha256')
      .update(value)
      .digest('hex')
      .slice(0, 8);

    return `<REDACTED:${type}:${hash}>`;
  }

  /**
   * Check if text contains any secrets (without modifying)
   *
   * @param text - Text to check
   * @returns true if secrets detected
   */
  hasSecrets(text: string): boolean {
    if (!text || text.length < 10) {
      return false;
    }

    for (const pattern of this.patterns) {
      pattern.pattern.lastIndex = 0;
      if (pattern.pattern.test(text)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Get detailed scan results without modifying text
   *
   * @param text - Text to scan
   * @returns Array of detected secrets with positions
   */
  scan(text: string): Array<{ type: SecretType; start: number; end: number; preview: string }> {
    const findings: Array<{ type: SecretType; start: number; end: number; preview: string }> = [];

    if (!text || text.length < 10) {
      return findings;
    }

    for (const pattern of this.patterns) {
      pattern.pattern.lastIndex = 0;
      let match;

      while ((match = pattern.pattern.exec(text)) !== null) {
        // Check entropy if required
        if (pattern.minEntropy) {
          const captured = match[1] || match[0];
          if (this.calculateEntropy(captured) < pattern.minEntropy) {
            continue;
          }
        }

        findings.push({
          type: pattern.type,
          start: match.index,
          end: match.index + match[0].length,
          preview: this.truncatePreview(match[0]),
        });
      }
    }

    return findings;
  }

  /**
   * Truncate secret for preview (show first 4 and last 4 chars)
   */
  private truncatePreview(secret: string): string {
    if (secret.length <= 12) {
      return '*'.repeat(secret.length);
    }
    return `${secret.slice(0, 4)}..${secret.slice(-4)}`;
  }
}

// =============================================================================
// SINGLETON EXPORT
// =============================================================================

/**
 * Default Gatekeeper instance for convenience
 */
export const gatekeeper = new Gatekeeper();

/**
 * Convenience function for one-off sanitization
 */
export function sanitize(text: string): SanitizeResult {
  return gatekeeper.sanitize(text);
}

/**
 * Convenience function for quick secret check
 */
export function hasSecrets(text: string): boolean {
  return gatekeeper.hasSecrets(text);
}
