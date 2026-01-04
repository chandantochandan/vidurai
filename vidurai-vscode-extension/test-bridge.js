/**
 * Simple test to verify Python bridge communication
 */
const { spawn } = require('child_process');
const path = require('path');

async function testBridge() {
    console.log('Testing Python bridge communication...\n');

    // Find Python (use venv Python which has Vidurai installed)
    const pythonCmd = path.join(__dirname, 'python-bridge', '.venv', 'bin', 'python');
    const bridgePath = path.join(__dirname, 'python-bridge', 'bridge.py');

    console.log(`Python command: ${pythonCmd}`);
    console.log(`Bridge path: ${bridgePath}\n`);

    // Spawn bridge
    const bridge = spawn(pythonCmd, [bridgePath], {
        stdio: ['pipe', 'pipe', 'pipe']
    });

    let responseReceived = false;

    // Handle stdout
    bridge.stdout.on('data', (data) => {
        const lines = data.toString().split('\n').filter(l => l.trim());
        for (const line of lines) {
            try {
                const response = JSON.parse(line);
                console.log('✅ Response received:', response);
                responseReceived = true;

                if (response.status === 'ok' && response.message === 'pong') {
                    console.log('\n✅ Bridge test PASSED!\n');
                    bridge.kill('SIGTERM');
                    process.exit(0);
                }
            } catch (error) {
                console.error('❌ Failed to parse response:', line);
            }
        }
    });

    // Handle stderr
    bridge.stderr.on('data', (data) => {
        console.log('Bridge stderr:', data.toString().trim());
    });

    // Handle exit
    bridge.on('exit', (code) => {
        if (!responseReceived) {
            console.error(`\n❌ Bridge test FAILED: Bridge exited with code ${code}\n`);
            process.exit(1);
        }
    });

    // Send ping
    setTimeout(() => {
        const ping = JSON.stringify({ type: 'ping', _id: 1 }) + '\n';
        console.log('Sending ping:', ping.trim());
        bridge.stdin.write(ping);
    }, 1000);

    // Timeout after 10 seconds
    setTimeout(() => {
        if (!responseReceived) {
            console.error('\n❌ Bridge test FAILED: Timeout\n');
            bridge.kill('SIGTERM');
            process.exit(1);
        }
    }, 10000);
}

testBridge().catch(error => {
    console.error('❌ Error:', error);
    process.exit(1);
});
