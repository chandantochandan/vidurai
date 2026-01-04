/**
 * Security Module Index
 *
 * Exports all security-related utilities for the Vidurai VS Code extension.
 *
 * @module security
 */

export {
  Gatekeeper,
  gatekeeper,
  sanitize,
  hasSecrets,
  type SecretType,
  type SanitizeResult,
} from './Gatekeeper';
