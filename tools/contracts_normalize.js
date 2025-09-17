#!/usr/bin/env node
/**
 * Contract Normalizer Helper
 * Provides utilities for normalizing API responses for drift detection
 */

// Volatile keys to ignore during drift detection
const VOLATILE_PATTERNS = [
  /.*_at$/,           // timestamps
  /.*_time$/,         // time fields  
  /^etag$/,           // cache tags
  /^trace_id$/,       // request tracing
  /^request_id$/,     // request correlation
  /^nonce$/,          // security nonces
  /^csrf_token$/,     // CSRF tokens
  /^session_id$/      // session identifiers
];

/**
 * Check if a key should be ignored during drift detection
 */
function isVolatileKey(key) {
  return VOLATILE_PATTERNS.some(pattern => pattern.test(key));
}

/**
 * Recursively sort object keys and remove volatile keys
 */
function normalizeObject(obj, path = '') {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return obj;
  }
  
  const normalized = {};
  const sortedKeys = Object.keys(obj).sort();
  
  for (const key of sortedKeys) {
    const keyPath = path ? `${path}.${key}` : key;
    
    // Skip volatile keys
    if (isVolatileKey(key)) {
      continue;
    }
    
    normalized[key] = normalizeObject(obj[key], keyPath);
  }
  
  return normalized;
}

/**
 * Mask sensitive values while preserving structure
 */
function maskSensitiveValues(obj) {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return obj;
  }
  
  const masked = {};
  
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'object' && value !== null) {
      masked[key] = maskSensitiveValues(value);
    } else if (typeof value === 'string' && value.length > 0) {
      // Mask string values but preserve structure
      masked[key] = '[MASKED]';
    } else {
      // Keep non-string values for structure
      masked[key] = value;
    }
  }
  
  return masked;
}

/**
 * Get all key paths from an object for comparison
 */
function getKeyPaths(obj, prefix = '') {
  const paths = [];
  
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return paths;
  }
  
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    paths.push(path);
    
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      paths.push(...getKeyPaths(value, path));
    }
  }
  
  return paths.sort();
}

/**
 * Compare two objects and return key-path differences
 */
function compareKeyPaths(obj1, obj2) {
  const paths1 = new Set(getKeyPaths(obj1));
  const paths2 = new Set(getKeyPaths(obj2));
  
  const added = [...paths2].filter(path => !paths1.has(path));
  const removed = [...paths1].filter(path => !paths2.has(path));
  
  return { added, removed };
}

module.exports = {
  isVolatileKey,
  normalizeObject,
  maskSensitiveValues,
  getKeyPaths,
  compareKeyPaths
};
