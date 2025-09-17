#!/usr/bin/env node
/**
 * Writer Minimalism Validator
 * Validates writer endpoint fixtures against lake rules
 */

const fs = require('fs');
const path = require('path');

// Configuration
const FIXTURES_DIR = 'tests/fixtures/writers';

// Exit codes
const EXIT_SUCCESS = 0;
const EXIT_VIOLATIONS = 1;
const EXIT_FIXTURE_ERROR = 2;
const EXIT_CONFIG_ERROR = 3;

// Recursive denylist keys
const DENYLIST_KEYS = [
  'user', 'profile', 'auth', 'birth_data', 'account', 'me',
  'session_id', 'csrf_token', 'password', 'email', 'first_name',
  'last_name', 'bio', 'birth_date', 'birth_time', 'birth_location',
  'human_design_data', 'sub_type'
];

/**
 * Normalize headers for consistent comparison
 */
function normalizeHeaders(headers) {
  const normalized = {};
  
  for (const [key, value] of Object.entries(headers)) {
    const normalizedKey = key.toLowerCase().trim();
    const normalizedValue = Array.isArray(value) ? value.join(', ') : String(value).trim();
    normalized[normalizedKey] = normalizedValue;
  }
  
  return normalized;
}

/**
 * Validate 204 No Content responses
 */
function validate204(fixture) {
  const { status_code, headers, body } = fixture;
  
  if (status_code !== 204) {
    return { valid: true, errors: [] };
  }
  
  const errors = [];
  const normalizedHeaders = normalizeHeaders(headers);
  
  // Empty body required
  if (body !== "" && body !== null && body !== undefined) {
    errors.push("204 responses must have empty body");
  }
  
  // Content-Length: 0 or absent (flexible per code review)
  const contentLength = normalizedHeaders['content-length'];
  if (contentLength !== undefined && contentLength !== '0') {
    errors.push("204 responses must have Content-Length: 0 or absent");
  }
  
  // Cache-Control: no-store required
  const cacheControl = normalizedHeaders['cache-control'];
  if (!cacheControl || !cacheControl.includes('no-store')) {
    errors.push("204 responses must include Cache-Control: no-store");
  }
  
  return { valid: errors.length === 0, errors };
}

/**
 * Validate 200 OK responses
 */
function validate200(fixture) {
  const { status_code, headers, body } = fixture;
  
  if (status_code !== 200) {
    return { valid: true, errors: [] };
  }
  
  const errors = [];
  const normalizedHeaders = normalizeHeaders(headers);
  
  let parsedBody;
  
  try {
    parsedBody = JSON.parse(body);
  } catch (e) {
    errors.push("200 responses must be valid JSON");
    return { valid: false, errors };
  }
  
  // Exactly {"status":"ok"} required (handle masked values)
  const expectedKeys = ["status"];
  const actualKeys = Object.keys(parsedBody).sort();
  
  if (JSON.stringify(actualKeys) !== JSON.stringify(expectedKeys)) {
    errors.push('200 responses must be exactly {"status":"ok"}');
  } else if (parsedBody.status !== "ok" && parsedBody.status !== "[MASKED]") {
    errors.push('200 responses must be exactly {"status":"ok"}');
  }
  
  // Cache-Control: no-store required
  const cacheControl = normalizedHeaders['cache-control'];
  if (!cacheControl || !cacheControl.includes('no-store')) {
    errors.push("200 responses must include Cache-Control: no-store");
  }
  
  return { valid: errors.length === 0, errors };
}

/**
 * Validate 201 Created responses
 */
function validate201(fixture) {
  const { status_code, headers, body } = fixture;
  
  if (status_code !== 201) {
    return { valid: true, errors: [] };
  }
  
  const errors = [];
  const normalizedHeaders = normalizeHeaders(headers);
  
  // Empty body required
  if (body !== "" && body !== null && body !== undefined) {
    errors.push("201 responses must have empty body");
  }
  
  // Location header required
  if (!normalizedHeaders['location']) {
    errors.push("201 responses must include Location header");
  }
  
  // Cache-Control: no-store required
  const cacheControl = normalizedHeaders['cache-control'];
  if (!cacheControl || !cacheControl.includes('no-store')) {
    errors.push("201 responses must include Cache-Control: no-store");
  }
  
  return { valid: errors.length === 0, errors };
}

/**
 * Recursively validate denylist keys
 */
function validateDenylist(obj, path = '') {
  const violations = [];
  
  if (typeof obj !== 'object' || obj === null) {
    return violations;
  }
  
  if (Array.isArray(obj)) {
    obj.forEach((item, index) => {
      const itemPath = path ? `${path}[${index}]` : `[${index}]`;
      violations.push(...validateDenylist(item, itemPath));
    });
    return violations;
  }
  
  for (const [key, value] of Object.entries(obj)) {
    const keyPath = path ? `${path}.${key}` : key;
    
    // Check if key is in denylist
    if (DENYLIST_KEYS.includes(key)) {
      violations.push(`Forbidden key found: ${keyPath}`);
    }
    
    // Recurse into nested objects
    if (typeof value === 'object' && value !== null) {
      violations.push(...validateDenylist(value, keyPath));
    }
  }
  
  return violations;
}

/**
 * Validate denylist in response body
 */
function validateResponseDenylist(fixture) {
  const { body } = fixture;
  
  if (!body || body.length === 0) {
    return { valid: true, violations: [] };
  }
  
  let parsedBody;
  
  try {
    parsedBody = JSON.parse(body);
  } catch (e) {
    // If not JSON, skip denylist validation
    return { valid: true, violations: [] };
  }
  
  const violations = validateDenylist(parsedBody);
  
  return { valid: violations.length === 0, violations };
}

/**
 * Validate a single fixture
 */
function validateFixture(fixture) {
  const results = {
    endpoint: fixture.endpoint,
    valid: true,
    errors: [],
    violations: []
  };
  
  // Validate status code rules
  const r204 = validate204(fixture);
  const r200 = validate200(fixture);
  const r201 = validate201(fixture);
  
  results.errors.push(...r204.errors, ...r200.errors, ...r201.errors);
  
  // Validate denylist
  const denylistResult = validateResponseDenylist(fixture);
  results.violations.push(...denylistResult.violations);
  
  results.valid = results.errors.length === 0 && results.violations.length === 0;
  
  return results;
}

/**
 * Load all fixtures from directory
 */
function loadFixtures() {
  const fixtures = [];
  
  try {
    const files = fs.readdirSync(FIXTURES_DIR);
    
    for (const file of files) {
      if (file.endsWith('.json') && file !== 'allowlist.json') {
        const filepath = path.join(FIXTURES_DIR, file);
        const content = fs.readFileSync(filepath, 'utf8');
        const fixture = JSON.parse(content);
        fixtures.push(fixture);
      }
    }
    
    return fixtures;
  } catch (error) {
    throw new Error(`Failed to load fixtures: ${error.message}`);
  }
}

/**
 * Print validation summary
 */
function printSummary(results) {
  const totalFixtures = results.length;
  const validFixtures = results.filter(r => r.valid).length;
  const invalidFixtures = totalFixtures - validFixtures;
  
  console.log(`\n📊 Validation Summary:`);
  console.log(`  Total fixtures: ${totalFixtures}`);
  console.log(`  Valid: ${validFixtures}`);
  console.log(`  Invalid: ${invalidFixtures}`);
  
  if (invalidFixtures > 0) {
    const totalErrors = results.reduce((sum, r) => sum + r.errors.length, 0);
    const totalViolations = results.reduce((sum, r) => sum + r.violations.length, 0);
    console.log(`  Rule errors: ${totalErrors}`);
    console.log(`  Denylist violations: ${totalViolations}`);
  }
}

/**
 * Print detailed validation results
 */
function printResults(results) {
  let hasViolations = false;
  
  for (const result of results) {
    if (!result.valid) {
      hasViolations = true;
      console.log(`\n❌ ${result.endpoint}:`);
      
      if (result.errors.length > 0) {
        console.log('  Rule violations:');
        result.errors.forEach(error => console.log(`    - ${error}`));
      }
      
      if (result.violations.length > 0) {
        console.log('  Denylist violations:');
        result.violations.forEach(violation => console.log(`    - ${violation}`));
      }
    } else {
      console.log(`✅ ${result.endpoint}`);
    }
  }
  
  return hasViolations;
}

/**
 * Main validation function
 */
function validateWriters() {
  try {
    console.log('Loading writer fixtures...');
    const fixtures = loadFixtures();
    
    if (fixtures.length === 0) {
      console.log('⚠️  No fixtures found. Run recorder first.');
      return EXIT_SUCCESS;
    }
    
    console.log(`Validating ${fixtures.length} writer fixtures...\n`);
    
    const results = fixtures.map(validateFixture);
    const hasViolations = printResults(results);
    
    printSummary(results);
    
    if (hasViolations) {
      console.log('\n❌ Writer minimalism violations detected');
      return EXIT_VIOLATIONS;
    } else {
      console.log('\n✅ All writers conform to minimalism rules');
      return EXIT_SUCCESS;
    }
    
  } catch (error) {
    console.error(`Validation error: ${error.message}`);
    return EXIT_FIXTURE_ERROR;
  }
}

/**
 * Main entry point
 */
function main() {
  // Check if fixtures directory exists
  if (!fs.existsSync(FIXTURES_DIR)) {
    console.error(`Error: Fixtures directory ${FIXTURES_DIR} not found`);
    console.error('Run the recorder first: pnpm contracts:record-writers');
    process.exit(EXIT_CONFIG_ERROR);
  }
  
  const exitCode = validateWriters();
  process.exit(exitCode);
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { 
  validateWriters, 
  validateFixture, 
  validate204, 
  validate200, 
  validate201, 
  validateDenylist 
};
