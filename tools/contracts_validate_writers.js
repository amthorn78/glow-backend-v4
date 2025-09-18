#!/usr/bin/env node
/**
 * Writer Minimalism Validator
 * Validates writer endpoint fixtures against lake rules.
 * This version enforces denylist regardless of headers and tightens status code rules.
 */

const fs = require('fs');
const path = require('path');

// --- Configuration ---
const FIXTURES_DIR = 'tests/fixtures/writers';
const DENYLIST_ROOT_KEYS = ['user', 'profile', 'auth', 'birth_data', 'account', 'me'];

// --- Exit Codes ---
const EXIT_SUCCESS = 0;
const EXIT_VIOLATIONS = 1;
const EXIT_FIXTURE_ERROR = 2;
const EXIT_CONFIG_ERROR = 3;

/**
 * Recursively finds all key paths in an object.
 * @param {object} obj - The object to inspect.
 * @returns {string[]} - An array of key paths (e.g., 'data.user.id').
 */
function getAllKeyPaths(obj, prefix = '') {
    if (typeof obj !== 'object' || obj === null) {
        return [];
    }
    return Object.keys(obj).reduce((acc, key) => {
        const newPrefix = prefix ? `${prefix}.${key}` : key;
        acc.push(newPrefix);
        if (typeof obj[key] === 'object' && obj[key] !== null) {
            acc.push(...getAllKeyPaths(obj[key], newPrefix));
        }
        return acc;
    }, []);
}


/**
 * Validates the body against a denylist of top-level keys.
 * @param {object} body - The response body.
 * @returns {string[]} - An array of violation messages.
 */
function validateDenylist(body) {
    const violations = [];
    const keyPaths = getAllKeyPaths(body);

    for (const keyPath of keyPaths) {
        const rootKey = keyPath.split('.')[0];
        if (DENYLIST_ROOT_KEYS.includes(rootKey)) {
            const violationMessage = `Forbidden key found at: ${rootKey}`;
            if (!violations.includes(violationMessage)) {
                violations.push(violationMessage);
            }
        }
    }
    return violations;
}


/**
 * Validates a single writer fixture against all rules.
 * @param {object} fixture - The fixture data.
 * @returns {object} - A result object with validity and errors.
 */
function validateFixture(fixture) {
    const { endpoint, status, headers, body } = fixture;
    const errors = [];

    const hasBody = body && typeof body === 'object' && Object.keys(body).length > 0;
    const normalizedHeaders = Object.entries(headers || {}).reduce((acc, [key, value]) => {
        acc[key.toLowerCase()] = value;
        return acc;
    }, {});

    switch (status) {
        case 204:
            if (hasBody) {
                errors.push('204 writer must have empty body');
            }
            break;
        case 201:
            if (hasBody) {
                errors.push('201 writer must have empty body');
            }
            if (!normalizedHeaders.location) {
                errors.push('201 writer requires Location header');
            }
            break;
        case 200:
            if (!hasBody) {
                 errors.push('200 writer must have a body');
            } else {
                const bodyKeys = Object.keys(body);
                if (bodyKeys.length !== 1 || bodyKeys[0] !== 'status' || body.status !== 'ok') {
                    const foundKeys = bodyKeys.filter(k => k !== 'status').join(',');
                    errors.push(`200 writer must be {"status":"ok"} (found keys: ${foundKeys || 'none'})`);
                }
            }
            break;
    }

    if (hasBody) {
        const denylistViolations = validateDenylist(body);
        errors.push(...denylistViolations);
    }

    return {
        endpoint,
        valid: errors.length === 0,
        errors,
    };
}

function loadFixtures() {
    if (!fs.existsSync(FIXTURES_DIR)) {
        console.error(`Error: Fixtures directory not found: ${FIXTURES_DIR}`);
        console.error('Run the recorder first: pnpm contracts:record-writers');
        process.exit(EXIT_CONFIG_ERROR);
    }

    try {
        return fs.readdirSync(FIXTURES_DIR)
            .filter(file => file.endsWith('.json'))
            .map(file => {
                const filepath = path.join(FIXTURES_DIR, file);
                const content = fs.readFileSync(filepath, 'utf8');
                const fixture = JSON.parse(content);
                fixture.filename = file;
                return fixture;
            });
    } catch (error) {
        console.error(`Failed to load or parse fixtures: ${error.message}`);
        process.exit(EXIT_FIXTURE_ERROR);
    }
}

function main() {
    console.log('Loading writer fixtures...');
    const fixtures = loadFixtures();

    if (fixtures.length === 0) {
        console.log('⚠️ No fixtures found to validate.');
        process.exit(EXIT_SUCCESS);
    }

    console.log(`Validating ${fixtures.length} writer fixtures...\n`);

    const results = fixtures.map(validateFixture);
    let hasViolations = false;

    results.forEach(result => {
        if (result.valid) {
            console.log(`✅ ${result.endpoint}`);
        } else {
            hasViolations = true;
            console.log(`\n❌ ${result.endpoint} (from ${result.filename || 'N/A'}):`);
            result.errors.forEach(error => console.log(`    - ${error}`));
        }
    });

    const invalidCount = results.filter(r => !r.valid).length;

    console.log(`\n📊 Validation Summary:`);
    console.log(`  Total fixtures: ${results.length}`);
    console.log(`  Valid: ${results.length - invalidCount}`);
    console.log(`  Invalid: ${invalidCount}`);

    if (hasViolations) {
        console.log('\n❌ Writer minimalism violations detected');
        process.exit(EXIT_VIOLATIONS);
    } else {
        console.log('\n✅ All writers conform to minimalism rules');
        process.exit(EXIT_SUCCESS);
    }
}

if (require.main === module) {
    main();
}

