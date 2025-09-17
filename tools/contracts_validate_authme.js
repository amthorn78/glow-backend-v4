#!/usr/bin/env node
/**
 * /auth/me Contract Drift Validator
 * Validates live API response against stored snapshot for drift detection
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const { normalizeObject, compareKeyPaths } = require('./contracts_normalize');

// Exit codes
const EXIT_SUCCESS = 0;
const EXIT_DRIFT = 1;
const EXIT_SCHEMA_VERSION_MISSING = 2;
const EXIT_AUTH_FAILED = 3;
const EXIT_ERROR = 4;

// Configuration
const TIMEOUT_MS = 7000;
const MAX_RETRIES = 1;

/**
 * Make HTTP request with timeout
 */
function makeRequest(options, postData = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          body: data
        });
      });
    });
    
    req.setTimeout(TIMEOUT_MS, () => {
      req.destroy();
      reject(new Error(`Request timeout after ${TIMEOUT_MS}ms`));
    });
    
    req.on('error', reject);
    
    if (postData) {
      req.write(postData);
    }
    
    req.end();
  });
}

/**
 * Perform login and return cookies
 */
async function login(baseUrl, email, password) {
  const loginUrl = new URL('/api/auth/login', baseUrl);
  
  const options = {
    hostname: loginUrl.hostname,
    port: loginUrl.port || 443,
    path: loginUrl.pathname,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'contract-validator/1.0'
    }
  };
  
  const postData = JSON.stringify({ email, password });
  
  try {
    const response = await makeRequest(options, postData);
    
    if (response.statusCode !== 200) {
      throw new Error(`Login failed with status ${response.statusCode}`);
    }
    
    const cookies = response.headers['set-cookie'] || [];
    return cookies.join('; ');
  } catch (error) {
    throw new Error(`Login request failed: ${error.message}`);
  }
}

/**
 * Fetch /auth/me with authentication
 */
async function fetchAuthMe(baseUrl, cookies) {
  const meUrl = new URL('/api/auth/me', baseUrl);
  
  const options = {
    hostname: meUrl.hostname,
    port: meUrl.port || 443,
    path: meUrl.pathname,
    method: 'GET',
    headers: {
      'Cookie': cookies,
      'User-Agent': 'contract-validator/1.0'
    }
  };
  
  try {
    const response = await makeRequest(options);
    
    return {
      statusCode: response.statusCode,
      data: response.statusCode === 200 ? JSON.parse(response.body) : null,
      rawBody: response.body
    };
  } catch (error) {
    throw new Error(`Auth/me request failed: ${error.message}`);
  }
}

/**
 * Validate with authentication retry logic
 */
async function validateWithAuth(baseUrl, email, password) {
  let cookies;
  let authAttempts = 0;
  
  // Initial login
  try {
    console.log('Attempting login...');
    cookies = await login(baseUrl, email, password);
    authAttempts++;
  } catch (error) {
    console.error(`Initial login failed: ${error.message}`);
    process.exit(EXIT_AUTH_FAILED);
  }
  
  // Fetch /auth/me
  let response = await fetchAuthMe(baseUrl, cookies);
  
  // Handle 401 with single retry
  if (response.statusCode === 401) {
    console.log('Auth failed, attempting re-authentication...');
    
    if (authAttempts >= MAX_RETRIES + 1) {
      console.error('AUTH_FAILED: Unable to authenticate after retry');
      process.exit(EXIT_AUTH_FAILED);
    }
    
    try {
      cookies = await login(baseUrl, email, password);
      authAttempts++;
      response = await fetchAuthMe(baseUrl, cookies);
      
      if (response.statusCode === 401) {
        console.error('AUTH_FAILED: Second authentication attempt failed');
        process.exit(EXIT_AUTH_FAILED);
      }
    } catch (error) {
      console.error(`Re-authentication failed: ${error.message}`);
      process.exit(EXIT_AUTH_FAILED);
    }
  }
  
  if (response.statusCode !== 200) {
    throw new Error(`Unexpected status code: ${response.statusCode}`);
  }
  
  return response.data;
}

/**
 * Load and validate snapshot file
 */
function loadSnapshot(snapshotPath) {
  try {
    const content = fs.readFileSync(snapshotPath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    throw new Error(`Failed to load snapshot: ${error.message}`);
  }
}

/**
 * Check schema version requirement
 */
function validateSchemaVersion(data) {
  if (!data.hasOwnProperty('schema_version')) {
    console.error('SCHEMA_VERSION_MISSING: schema_version field is required');
    process.exit(EXIT_SCHEMA_VERSION_MISSING);
  }
  
  if (data.schema_version !== 'v1') {
    console.error(`SCHEMA_VERSION_MISMATCH: Expected 'v1', got '${data.schema_version}'`);
    process.exit(EXIT_DRIFT);
  }
}

/**
 * Validate pointer file
 */
function validatePointer(pointerPath) {
  try {
    const content = fs.readFileSync(pointerPath, 'utf8').trim();
    if (content !== 'v1') {
      throw new Error(`Pointer file should contain 'v1', got '${content}'`);
    }
    console.log('✅ Pointer validation passed: current.version = v1');
  } catch (error) {
    throw new Error(`Pointer validation failed: ${error.message}`);
  }
}

/**
 * Main validation function
 */
async function validate(options) {
  const {
    snapshotPath,
    livePath,
    baseUrl,
    email,
    password,
    pointerPath
  } = options;
  
  try {
    // Validate pointer file
    if (pointerPath) {
      validatePointer(pointerPath);
    }
    
    // Load snapshot
    console.log(`Loading snapshot from ${snapshotPath}...`);
    const snapshot = loadSnapshot(snapshotPath);
    
    let liveData;
    
    if (livePath) {
      // Load from file
      console.log(`Loading live data from ${livePath}...`);
      const content = fs.readFileSync(livePath, 'utf8');
      liveData = JSON.parse(content);
    } else {
      // Fetch from API
      console.log(`Fetching live data from ${baseUrl}/api/auth/me...`);
      liveData = await validateWithAuth(baseUrl, email, password);
    }
    
    // Validate schema version
    validateSchemaVersion(liveData);
    console.log('✅ Schema version validation passed');
    
    // Normalize both objects for comparison
    const normalizedSnapshot = normalizeObject(snapshot);
    const normalizedLive = normalizeObject(liveData);
    
    // Compare key paths
    const diff = compareKeyPaths(normalizedSnapshot, normalizedLive);
    
    if (diff.added.length > 0 || diff.removed.length > 0) {
      console.error('❌ Contract drift detected:');
      
      if (diff.added.length > 0) {
        console.error('  Added keys:');
        diff.added.forEach(key => console.error(`    + ${key}`));
      }
      
      if (diff.removed.length > 0) {
        console.error('  Removed keys:');
        diff.removed.forEach(key => console.error(`    - ${key}`));
      }
      
      process.exit(EXIT_DRIFT);
    }
    
    console.log('✅ No contract drift detected - validation passed');
    process.exit(EXIT_SUCCESS);
    
  } catch (error) {
    console.error(`Validation error: ${error.message}`);
    process.exit(EXIT_ERROR);
  }
}

/**
 * Parse command line arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {};
  
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i];
    const value = args[i + 1];
    
    switch (key) {
      case '--snapshot':
        options.snapshotPath = value;
        break;
      case '--live':
        options.livePath = value;
        break;
      case '--base-url':
        options.baseUrl = value;
        break;
      case '--email':
        options.email = value;
        break;
      case '--password':
        options.password = value;
        break;
      case '--pointer':
        options.pointerPath = value;
        break;
      case '--timeout':
        // Timeout is handled by constant, but accept for compatibility
        break;
      default:
        console.error(`Unknown option: ${key}`);
        process.exit(EXIT_ERROR);
    }
  }
  
  return options;
}

/**
 * Main entry point
 */
async function main() {
  const options = parseArgs();
  
  // Validate required options
  if (!options.snapshotPath) {
    console.error('Error: --snapshot is required');
    process.exit(EXIT_ERROR);
  }
  
  if (!options.livePath && (!options.baseUrl || !options.email || !options.password)) {
    console.error('Error: Either --live or (--base-url, --email, --password) is required');
    process.exit(EXIT_ERROR);
  }
  
  await validate(options);
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error(`Unexpected error: ${error.message}`);
    process.exit(EXIT_ERROR);
  });
}

module.exports = { validate, validateSchemaVersion, validatePointer };
