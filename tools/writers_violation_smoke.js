#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const FIXTURE_PATH = path.join(__dirname, '..', 'tests', 'fixtures', 'writers', '_tmp_violation.json');

const VIOLATION_FIXTURE = {
  endpoint: "/api/_tmp_violation",
  method: "POST",
  status: 200,
  headers: { "cache-control": "no-store" },
  body: { data: { user: { email: "[MASKED]" } } }
};

function runCommand(command) {
    try {
        console.log(`\n> Running: ${command}`);
        const output = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
        console.log(output);
        return { success: true, output };
    } catch (error) {
        console.error(error.stdout);
        console.error(error.stderr);
        return { success: false, error };
    }
}

function main() {
    let exitCode = 0;
    try {
        console.log('--- Running Writer Validator Negative Smoke Test ---');

        // 1. Write the violation fixture
        console.log(`\n[1/4] Creating temporary violation fixture at ${FIXTURE_PATH}...`);
        fs.mkdirSync(path.dirname(FIXTURE_PATH), { recursive: true });
        fs.writeFileSync(FIXTURE_PATH, JSON.stringify(VIOLATION_FIXTURE, null, 2));
        console.log('Fixture created.');

        // 2. Run validator, expecting it to fail
        console.log('\n[2/4] Running validator (expecting failure)...\n');
        const validationResult = runCommand('pnpm contracts:validate-writers');

        if (validationResult.success) {
            console.error('\n❌ FAIL: Negative test unexpectedly passed.');
            exitCode = 1;
        } else {
            const output = validationResult.error.stdout.toString();
            if (output.includes('Forbidden key found at: data') || output.includes('200 writer must be {"status":"ok"}')) {
                console.log('\n✅ PASS: Validator failed as expected.');
            } else {
                console.error('\n❌ FAIL: Validator failed, but for the wrong reason.');
                exitCode = 1;
            }
        }
    } catch (error) {
        console.error(`\nAn unexpected error occurred: ${error.message}`);
        exitCode = 1;
    } finally {
        // 3. Clean up the fixture
        console.log('\n[3/4] Cleaning up temporary fixture...');
        if (fs.existsSync(FIXTURE_PATH)) {
            fs.unlinkSync(FIXTURE_PATH);
            console.log('Fixture deleted.');
        } else {
            console.log('Fixture already deleted.');
        }

        // 4. Re-run validator, expecting it to pass
        console.log('\n[4/4] Re-running validator (expecting success)...');
        const finalValidation = runCommand('pnpm contracts:validate-writers');

        if (!finalValidation.success) {
            console.error('\n❌ FAIL: Validator failed on cleanup run.');
            exitCode = 1;
        } else {
            console.log('\n✅ PASS: Validator succeeded on cleanup run.');
        }

        console.log(`\n--- Test Complete ---`);
        process.exit(exitCode);
    }
}

if (require.main === module) {
    main();
}

