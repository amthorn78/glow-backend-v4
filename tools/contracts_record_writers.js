#!/usr/bin/env node
/**
 * Writer Endpoints Recorder
 * Records writer endpoint responses for minimalism validation
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// Configuration
const TIMEOUT_MS = 7000;
const FIXTURES_DIR = 'tests/fixtures/writers';
const ALLOWLIST_FILE = path.join(FIXTURES_DIR, 'allowlist.json');

// Exit codes
const EXIT_SUCCESS = 0;
const EXIT_NETWORK_ERROR = 1;
const EXIT_FILE_ERROR = 2;

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
 * Mask sensitive values in response body
 */
function maskResponseBody(body, contentType) {
  if (!body || body.length === 0) {
    return body;
  }
  
  // Only attempt to parse JSON responses
  if (contentType && contentType.includes('application/json')) {
    try {
      const parsed = JSON.parse(body);
      const masked = maskSensitiveObject(parsed);
      return JSON.stringify(masked);
    } catch (e) {
      // If parsing fails, return original body
      return body;
    }
  }
  
  return body;
}

/**
 * Recursively mask sensitive values in objects
 */
function maskSensitiveObject(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => maskSensitiveObject(item));
  }
  
  const masked = {};
  
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'string' && value.length > 0) {
      masked[key] = '[MASKED]';
    } else if (typeof value === 'object' && value !== null) {
      masked[key] = maskSensitiveObject(value);
    } else {
      masked[key] = value;
    }
  }
  
  return masked;
}

/**
 * Check if error is transient and should be retried
 */
function isTransientError(error, statusCode) {
  // Retry on 502/503/504 (transient server errors)
  if (statusCode === 502 || statusCode === 503 || statusCode === 504) {
    return true;
  }
  
  // Retry on network/socket errors
  const transientCodes = ['ECONNRESET', 'ETIMEDOUT', 'ENOTFOUND', 'ECONNREFUSED'];
  return transientCodes.some(code => error.message.includes(code));
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
      'User-Agent': 'writer-recorder/1.0'
    }
  };
  
  const postData = JSON.stringify({ email, password });
  
  try {
    const response = await makeRequest(options, postData);
    
    if (response.statusCode === 200) {
      const cookies = response.headers['set-cookie'] || [];
      return cookies.join('; ');
    }
    
    // Check if we should retry on transient errors
    if (isTransientError(null, response.statusCode)) {
      console.log(`auth_retry=1 status=${response.statusCode}`);
      
      // Wait 200-300ms with jitter
      const jitter = 200 + Math.random() * 100;
      await new Promise(resolve => setTimeout(resolve, jitter));
      
      const retryResponse = await makeRequest(options, postData);
      if (retryResponse.statusCode !== 200) {
        throw new Error(`Login failed with status ${retryResponse.statusCode} (after retry)`);
      }
      
      const cookies = retryResponse.headers['set-cookie'] || [];
      return cookies.join('; ');
    }
    
    throw new Error(`Login failed with status ${response.statusCode}`);
  } catch (error) {
    // Check if we should retry on network errors
    if (isTransientError(error, null)) {
      console.log(`auth_retry=1 error=${error.code || 'network'}`);
      
      // Wait 200-300ms with jitter
      const jitter = 200 + Math.random() * 100;
      await new Promise(resolve => setTimeout(resolve, jitter));
      
      try {
        const retryResponse = await makeRequest(options, postData);
        if (retryResponse.statusCode !== 200) {
          throw new Error(`Login failed with status ${retryResponse.statusCode} (after retry)`);
        }
        
        const cookies = retryResponse.headers['set-cookie'] || [];
        return cookies.join('; ');
      } catch (retryError) {
        throw new Error(`Login request failed: ${retryError.message} (after retry)`);
      }
    }
    
    throw new Error(`Login request failed: ${error.message}`);
  }
}

/**
 * Record a single writer endpoint
 */
async function recordEndpoint(baseUrl, cookies, method, path) {
  const url = new URL(path, baseUrl);
  
  const options = {
    hostname: url.hostname,
    port: url.port || 443,
    path: url.pathname,
    method: method,
    headers: {
      'Cookie': cookies,
      'User-Agent': 'writer-recorder/1.0'
    }
  };
  
  // Add Content-Type for POST/PUT requests
  if (method === 'POST' || method === 'PUT') {
    options.headers['Content-Type'] = 'application/json';
  }
  
  let postData = null;
  
  // Provide minimal test data for different endpoints
  if (method === 'POST' || method === 'PUT') {
    if (path.includes('/profile/basic-info')) {
      postData = JSON.stringify({ first_name: 'Test', last_name: 'User' });
    } else if (path.includes('/profile/birth-data')) {
      postData = JSON.stringify({ birth_date: '1990-01-01' });
    } else if (path.includes('/priorities')) {
      postData = JSON.stringify({ priorities: [] });
    } else if (path.includes('/compatibility/calculate')) {
      postData = JSON.stringify({ target_user_id: 1 });
    }
  }
  
  try {
    const response = await makeRequest(options, postData);
    
    const normalizedHeaders = normalizeHeaders(response.headers);
    const contentType = normalizedHeaders['content-type'] || '';
    const maskedBody = maskResponseBody(response.body, contentType);
    
    return {
      endpoint: `${method} ${path}`,
      status_code: response.statusCode,
      headers: normalizedHeaders,
      body: maskedBody,
      recorded_at: '[TIMESTAMP_REDACTED]',
      masked: true
    };
  } catch (error) {
    console.warn(`Failed to record ${method} ${path}: ${error.message}`);
    return null;
  }
}

/**
 * Load allowlist from file
 */
function loadAllowlist() {
  try {
    const content = fs.readFileSync(ALLOWLIST_FILE, 'utf8');
    const allowlist = JSON.parse(content);
    return allowlist.endpoints || [];
  } catch (error) {
    throw new Error(`Failed to load allowlist: ${error.message}`);
  }
}

/**
 * Save fixture to file
 */
function saveFixture(fixture) {
  const sanitizedPath = fixture.endpoint
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
  
  const filename = `${sanitizedPath}.json`;
  const filepath = path.join(FIXTURES_DIR, filename);
  
  try {
    fs.writeFileSync(filepath, JSON.stringify(fixture, null, 2));
    console.log(`✅ Recorded: ${fixture.endpoint} → ${filename}`);
  } catch (error) {
    console.error(`❌ Failed to save ${filename}: ${error.message}`);
    throw error;
  }
}

/**
 * Main recording function
 */
async function recordWriters(baseUrl, email, password) {
  try {
    // Load allowlist
    console.log('Loading endpoint allowlist...');
    const endpoints = loadAllowlist();
    console.log(`Found ${endpoints.length} allowlisted endpoints`);
    
    // Login
    console.log('Authenticating...');
    const cookies = await login(baseUrl, email, password);
    
    // Record each endpoint
    const fixtures = [];
    
    for (const endpoint of endpoints) {
      console.log(`Recording ${endpoint.method} ${endpoint.path}...`);
      const fixture = await recordEndpoint(baseUrl, cookies, endpoint.method, endpoint.path);
      
      if (fixture) {
        fixtures.push(fixture);
        saveFixture(fixture);
      }
    }
    
    console.log(`\n✅ Recording complete: ${fixtures.length} fixtures created`);
    return fixtures;
    
  } catch (error) {
    console.error(`Recording failed: ${error.message}`);
    throw error;
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
      case '--base-url':
        options.baseUrl = value;
        break;
      case '--email':
        options.email = value;
        break;
      case '--password':
        options.password = value;
        break;
      default:
        console.error(`Unknown option: ${key}`);
        process.exit(EXIT_FILE_ERROR);
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
  if (!options.baseUrl || !options.email || !options.password) {
    console.error('Error: --base-url, --email, and --password are required');
    process.exit(EXIT_FILE_ERROR);
  }
  
  try {
    await recordWriters(options.baseUrl, options.email, options.password);
    process.exit(EXIT_SUCCESS);
  } catch (error) {
    console.error(`Recording error: ${error.message}`);
    process.exit(EXIT_NETWORK_ERROR);
  }
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error(`Unexpected error: ${error.message}`);
    process.exit(EXIT_NETWORK_ERROR);
  });
}

module.exports = { recordWriters, loadAllowlist };
