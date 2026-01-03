"use strict";
/**
 * Codex Bridge Extension
 *
 * Integrates with OpenAI Codex extension (openai.chatgpt) to enable
 * automatic AI debate invocation.
 *
 * Supports multiple integration modes:
 * 1. Command invocation (if Codex exposes commands)
 * 2. Extension API (if Codex exports API)
 * 3. Clipboard automation (fallback - simulates copy/paste)
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const http = __importStar(require("http"));
const clipboardy_1 = __importDefault(require("clipboardy"));
let server = null;
let serverPort = 8765;
let codexExtension = null;
let integrationMode = null;
function activate(context) {
    console.log('Codex Bridge extension activated');
    // Find Codex extension
    codexExtension = vscode.extensions.getExtension('openai.chatgpt') || null;
    if (!codexExtension) {
        vscode.window.showWarningMessage('Codex extension (openai.chatgpt) not found. Install it first.');
    }
    else {
        console.log(`Codex extension found: v${codexExtension.packageJSON.version}`);
    }
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('codex-bridge.start', () => startServer()), vscode.commands.registerCommand('codex-bridge.stop', () => stopServer()), vscode.commands.registerCommand('codex-bridge.status', () => checkStatus()), vscode.commands.registerCommand('codex-bridge.investigate', () => investigateCodex()));
    // Auto-start server if configured
    const config = vscode.workspace.getConfiguration('codexBridge');
    const autoStart = config.get('autoStart', true);
    if (autoStart) {
        startServer();
    }
}
function deactivate() {
    stopServer();
}
/**
 * Investigate Codex extension to determine integration method
 */
async function investigateCodex() {
    const output = vscode.window.createOutputChannel('Codex Bridge Investigation');
    output.show();
    output.appendLine('=== Investigating Codex Extension ===\n');
    if (!codexExtension) {
        output.appendLine('❌ Codex extension not found');
        return;
    }
    output.appendLine(`✅ Extension ID: ${codexExtension.id}`);
    output.appendLine(`✅ Version: ${codexExtension.packageJSON.version}`);
    output.appendLine(`✅ Active: ${codexExtension.isActive}\n`);
    // Check commands
    output.appendLine('=== Available Commands ===');
    const allCommands = await vscode.commands.getCommands(true);
    const codexCommands = allCommands.filter(cmd => cmd.toLowerCase().includes('chatgpt') ||
        cmd.toLowerCase().includes('codex') ||
        cmd.toLowerCase().includes('openai'));
    if (codexCommands.length > 0) {
        output.appendLine(`Found ${codexCommands.length} Codex-related commands:`);
        codexCommands.forEach(cmd => output.appendLine(`  - ${cmd}`));
        integrationMode = 'command';
        output.appendLine('\n✅ Integration Mode: COMMAND (can invoke commands)');
    }
    else {
        output.appendLine('No Codex commands found');
    }
    // Check package.json contributions
    output.appendLine('\n=== Contributed Commands (from package.json) ===');
    if (codexExtension.packageJSON.contributes?.commands) {
        codexExtension.packageJSON.contributes.commands.forEach((cmd) => {
            output.appendLine(`  - ${cmd.command}: ${cmd.title}`);
        });
    }
    else {
        output.appendLine('No commands contributed');
    }
    // Check API
    output.appendLine('\n=== Extension API ===');
    if (!codexExtension.isActive) {
        await codexExtension.activate();
    }
    const api = codexExtension.exports;
    if (api) {
        output.appendLine('✅ Extension exports API');
        output.appendLine(`API keys: ${Object.keys(api).join(', ')}`);
        if (!integrationMode) {
            integrationMode = 'api';
            output.appendLine('\n✅ Integration Mode: API (can use exported API)');
        }
    }
    else {
        output.appendLine('❌ No API exported');
    }
    // If no integration found, use clipboard
    if (!integrationMode) {
        integrationMode = 'clipboard';
        output.appendLine('\n⚠️ Integration Mode: CLIPBOARD (fallback - will automate copy/paste)');
    }
    output.appendLine('\n=== Investigation Complete ===');
    output.appendLine(`\nRecommended integration mode: ${integrationMode?.toUpperCase()}`);
    vscode.window.showInformationMessage(`Codex Bridge: Using ${integrationMode?.toUpperCase()} integration mode`);
}
/**
 * Start the HTTP server
 */
async function startServer() {
    if (server) {
        vscode.window.showInformationMessage('Codex Bridge server is already running');
        return;
    }
    // Auto-investigate if not done yet
    if (!integrationMode) {
        await investigateCodex();
    }
    const config = vscode.workspace.getConfiguration('codexBridge');
    serverPort = config.get('port', 8765);
    server = http.createServer(async (req, res) => {
        // Enable CORS
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        // Handle OPTIONS preflight
        if (req.method === 'OPTIONS') {
            res.writeHead(200);
            res.end();
            return;
        }
        // Handle POST /invoke-codex
        if (req.method === 'POST' && req.url === '/invoke-codex') {
            await handleCodexInvoke(req, res);
        }
        // Handle GET /health
        else if (req.method === 'GET' && req.url === '/health') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                status: 'ok',
                port: serverPort,
                integration_mode: integrationMode,
                codex_available: !!codexExtension
            }));
        }
        // 404 for other routes
        else {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Not found' }));
        }
    });
    server.listen(serverPort, () => {
        vscode.window.showInformationMessage(`Codex Bridge server started on port ${serverPort} (${integrationMode} mode)`);
        console.log(`Codex Bridge listening on http://localhost:${serverPort}`);
        console.log(`Integration mode: ${integrationMode}`);
    });
    server.on('error', (err) => {
        vscode.window.showErrorMessage(`Codex Bridge server error: ${err.message}`);
        server = null;
    });
}
/**
 * Stop the HTTP server
 */
function stopServer() {
    if (server) {
        server.close(() => {
            vscode.window.showInformationMessage('Codex Bridge server stopped');
            console.log('Codex Bridge server stopped');
        });
        server = null;
    }
    else {
        vscode.window.showInformationMessage('Codex Bridge server is not running');
    }
}
/**
 * Check server status
 */
function checkStatus() {
    if (server) {
        vscode.window.showInformationMessage(`Codex Bridge: Running on port ${serverPort} (${integrationMode} mode)`);
    }
    else {
        vscode.window.showInformationMessage('Codex Bridge: Not running');
    }
}
/**
 * Handle /invoke-codex endpoint
 */
async function handleCodexInvoke(req, res) {
    try {
        // Parse request body
        const body = await parseRequestBody(req);
        const { prompt } = body;
        if (!prompt) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Missing prompt parameter' }));
            return;
        }
        if (!codexExtension) {
            res.writeHead(503, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                error: 'Codex extension not available',
                message: 'Install openai.chatgpt extension'
            }));
            return;
        }
        // Invoke Codex using detected integration mode
        let response;
        try {
            if (integrationMode === 'command') {
                response = await invokeViaCommand(prompt);
            }
            else if (integrationMode === 'api') {
                response = await invokeViaAPI(prompt);
            }
            else {
                // Clipboard mode (fallback)
                response = await invokeViaClipboard(prompt);
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                success: true,
                response: response,
                integration_mode: integrationMode,
                model: 'gpt-5-codex-max'
            }));
        }
        catch (error) {
            console.error('Error invoking Codex:', error);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                error: 'Failed to invoke Codex',
                message: error.message,
                integration_mode: integrationMode
            }));
        }
    }
    catch (error) {
        console.error('Error handling request:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            error: 'Internal server error',
            message: error.message
        }));
    }
}
/**
 * Invoke Codex via command (if available)
 */
async function invokeViaCommand(prompt) {
    console.log('Attempting command invocation...');
    // Try common command patterns
    const possibleCommands = [
        'chatgpt.ask',
        'chatgpt.chat',
        'chatgpt.sendMessage',
        'openai.chat',
        'codex.ask'
    ];
    for (const command of possibleCommands) {
        try {
            const result = await vscode.commands.executeCommand(command, prompt);
            if (result) {
                return String(result);
            }
        }
        catch (error) {
            console.log(`Command ${command} not found or failed`);
        }
    }
    throw new Error('No working Codex command found. Falling back to clipboard mode.');
}
/**
 * Invoke Codex via API (if exposed)
 */
async function invokeViaAPI(prompt) {
    console.log('Attempting API invocation...');
    if (!codexExtension || !codexExtension.isActive) {
        throw new Error('Codex extension not active');
    }
    const api = codexExtension.exports;
    if (!api) {
        throw new Error('Codex extension does not export API');
    }
    // Try common API method patterns
    const possibleMethods = ['ask', 'chat', 'sendMessage', 'query', 'invoke'];
    for (const method of possibleMethods) {
        if (typeof api[method] === 'function') {
            try {
                const result = await api[method](prompt);
                return String(result);
            }
            catch (error) {
                console.log(`API method ${method} failed:`, error);
            }
        }
    }
    throw new Error('No working API method found. Falling back to clipboard mode.');
}
/**
 * Invoke Codex via clipboard automation (fallback)
 */
async function invokeViaClipboard(prompt) {
    console.log('Using clipboard automation (fallback mode)...');
    vscode.window.showInformationMessage('Codex Bridge: Using clipboard automation. Opening Codex chat...');
    // 1. Save current clipboard
    let originalClipboard = '';
    try {
        originalClipboard = await clipboardy_1.default.read();
    }
    catch (error) {
        console.log('Could not read clipboard:', error);
    }
    // 2. Copy prompt to clipboard
    await clipboardy_1.default.write(prompt);
    // 3. Open Codex chat
    try {
        await vscode.commands.executeCommand('chatgpt.openView');
    }
    catch (error) {
        console.log('Could not open Codex view:', error);
    }
    // 4. Show instructions to user
    const action = await vscode.window.showInformationMessage('Codex Bridge: Prompt copied to clipboard. Please:\n' +
        '1. Paste it in Codex chat (Ctrl+V)\n' +
        '2. Wait for response\n' +
        '3. Copy Codex response (select all, Ctrl+C)\n' +
        '4. Click "Submit Response" button', 'Submit Response', 'Cancel');
    if (action !== 'Submit Response') {
        throw new Error('User cancelled clipboard automation');
    }
    // 5. Read response from clipboard
    const response = await clipboardy_1.default.read();
    // 6. Restore original clipboard
    try {
        await clipboardy_1.default.write(originalClipboard);
    }
    catch (error) {
        console.log('Could not restore clipboard:', error);
    }
    if (!response || response === prompt) {
        throw new Error('No valid response found in clipboard');
    }
    return response;
}
/**
 * Parse HTTP request body
 */
function parseRequestBody(req) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', (chunk) => {
            body += chunk.toString();
        });
        req.on('end', () => {
            try {
                const parsed = JSON.parse(body);
                resolve(parsed);
            }
            catch (error) {
                reject(new Error('Invalid JSON in request body'));
            }
        });
        req.on('error', (error) => {
            reject(error);
        });
    });
}
//# sourceMappingURL=extension.js.map