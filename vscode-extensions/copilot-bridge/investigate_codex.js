// Investigation script to find Codex extension commands
// Run this in VS Code Developer Console

const vscode = require('vscode');

async function investigateCodexExtension() {
    console.log('=== Investigating Codex Extension ===\n');

    // 1. Find the extension
    const extension = vscode.extensions.getExtension('openai.chatgpt');

    if (!extension) {
        console.log('ERROR: Codex extension not found!');
        console.log('Installed extensions:', vscode.extensions.all.map(e => e.id));
        return;
    }

    console.log('✅ Extension found:', extension.id);
    console.log('Version:', extension.packageJSON.version);
    console.log('Active:', extension.isActive);

    // 2. Get all available commands
    console.log('\n=== All VS Code Commands ===');
    const allCommands = await vscode.commands.getCommands(true);
    const codexCommands = allCommands.filter(cmd =>
        cmd.includes('chatgpt') ||
        cmd.includes('codex') ||
        cmd.includes('openai')
    );

    console.log('Codex-related commands:');
    codexCommands.forEach(cmd => console.log(`  - ${cmd}`));

    // 3. Check package.json for contributed commands
    console.log('\n=== Commands from package.json ===');
    if (extension.packageJSON.contributes && extension.packageJSON.contributes.commands) {
        extension.packageJSON.contributes.commands.forEach(cmd => {
            console.log(`  - ${cmd.command}: ${cmd.title}`);
        });
    }

    // 4. Check if extension exposes an API
    console.log('\n=== Extension API ===');
    if (!extension.isActive) {
        await extension.activate();
    }

    const api = extension.exports;
    console.log('API exported:', !!api);
    if (api) {
        console.log('API methods:', Object.keys(api));
    }

    // 5. Try to invoke chat command (if exists)
    console.log('\n=== Testing Command Invocation ===');
    try {
        // Try common command patterns
        const testCommands = [
            'chatgpt.ask',
            'chatgpt.chat',
            'chatgpt.send',
            'openai.chat',
            'codex.chat'
        ];

        for (const cmd of testCommands) {
            if (codexCommands.includes(cmd)) {
                console.log(`Found command: ${cmd}`);
            }
        }
    } catch (error) {
        console.log('Error testing commands:', error.message);
    }

    console.log('\n=== Investigation Complete ===');
}

// Export for use
module.exports = { investigateCodexExtension };
