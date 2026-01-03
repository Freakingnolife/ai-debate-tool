/**
 * Copilot Bridge Extension
 *
 * Exposes GitHub Copilot Language Model API via HTTP server for AI Debate Tool.
 * Enables 100% automation without API costs by leveraging local Copilot Pro+ subscription.
 */

import * as vscode from 'vscode';
import * as http from 'http';

let server: http.Server | null = null;
let serverPort: number = 8765;

export function activate(context: vscode.ExtensionContext) {
    console.log('Copilot Bridge extension activated');

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('copilot-bridge.start', () => startServer()),
        vscode.commands.registerCommand('copilot-bridge.stop', () => stopServer()),
        vscode.commands.registerCommand('copilot-bridge.status', () => checkStatus())
    );

    // Auto-start server if configured
    const config = vscode.workspace.getConfiguration('copilotBridge');
    const autoStart = config.get<boolean>('autoStart', true);

    if (autoStart) {
        startServer();
    }
}

export function deactivate() {
    stopServer();
}

/**
 * Start the HTTP server for Copilot bridge
 */
async function startServer() {
    if (server) {
        vscode.window.showInformationMessage('Copilot Bridge server is already running');
        return;
    }

    const config = vscode.workspace.getConfiguration('copilotBridge');
    serverPort = config.get<number>('port', 8765);

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

        // Handle POST /invoke-copilot
        if (req.method === 'POST' && req.url === '/invoke-copilot') {
            await handleCopilotInvoke(req, res);
        }
        // Handle GET /health
        else if (req.method === 'GET' && req.url === '/health') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'ok', port: serverPort }));
        }
        // 404 for other routes
        else {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Not found' }));
        }
    });

    server.listen(serverPort, () => {
        vscode.window.showInformationMessage(`Copilot Bridge server started on port ${serverPort}`);
        console.log(`Copilot Bridge listening on http://localhost:${serverPort}`);
    });

    server.on('error', (err) => {
        vscode.window.showErrorMessage(`Copilot Bridge server error: ${err.message}`);
        server = null;
    });
}

/**
 * Stop the HTTP server
 */
function stopServer() {
    if (server) {
        server.close(() => {
            vscode.window.showInformationMessage('Copilot Bridge server stopped');
            console.log('Copilot Bridge server stopped');
        });
        server = null;
    } else {
        vscode.window.showInformationMessage('Copilot Bridge server is not running');
    }
}

/**
 * Check server status
 */
function checkStatus() {
    if (server) {
        vscode.window.showInformationMessage(`Copilot Bridge server is running on port ${serverPort}`);
    } else {
        vscode.window.showInformationMessage('Copilot Bridge server is not running');
    }
}

/**
 * Handle /invoke-copilot endpoint
 */
async function handleCopilotInvoke(req: http.IncomingMessage, res: http.ServerResponse) {
    try {
        // Parse request body
        const body = await parseRequestBody(req);
        const { prompt, model } = body;

        if (!prompt) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Missing prompt parameter' }));
            return;
        }

        // Get Copilot model
        const preferredModel = model || vscode.workspace.getConfiguration('copilotBridge').get<string>('preferredModel', 'gpt-5-codex');

        const copilotModel = await getCopilotModel(preferredModel);

        if (!copilotModel) {
            res.writeHead(503, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                error: 'Copilot not available',
                message: 'GitHub Copilot is not active. Please ensure you have Copilot Pro+ subscription and the extension is enabled.'
            }));
            return;
        }

        // Send prompt to Copilot
        console.log(`Sending prompt to Copilot model: ${copilotModel.name}`);

        const messages = [
            vscode.LanguageModelChatMessage.User(prompt)
        ];

        const chatResponse = await copilotModel.sendRequest(messages, {}, new vscode.CancellationTokenSource().token);

        // Collect streaming response
        let fullResponse = '';
        for await (const chunk of chatResponse.text) {
            fullResponse += chunk;
        }

        console.log(`Copilot response received (${fullResponse.length} chars)`);

        // Send response
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            success: true,
            response: fullResponse,
            model: copilotModel.name,
            vendor: copilotModel.vendor
        }));

    } catch (error: any) {
        console.error('Error invoking Copilot:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            error: 'Internal server error',
            message: error.message
        }));
    }
}

/**
 * Get Copilot language model
 */
async function getCopilotModel(preferredModel: string): Promise<vscode.LanguageModelChat | null> {
    try {
        // Get all available language models
        const models = await vscode.lm.selectChatModels();

        if (models.length === 0) {
            console.log('No language models available');
            return null;
        }

        console.log(`Available models: ${models.map(m => m.name).join(', ')}`);

        // Try to find preferred model
        let selectedModel: vscode.LanguageModelChat | null = null;

        if (preferredModel === 'auto') {
            // Use first available model
            selectedModel = models[0];
        } else if (preferredModel === 'gpt-5-codex') {
            // Look for GPT-5.1-Codex (Codex 5.1 Max)
            selectedModel = models.find(m =>
                m.name.toLowerCase().includes('gpt-5') &&
                m.name.toLowerCase().includes('codex')
            ) || models.find(m =>
                m.name.toLowerCase().includes('codex')
            ) || null;
        } else if (preferredModel === 'gpt-5') {
            // Look for GPT-5
            selectedModel = models.find(m =>
                m.name.toLowerCase().includes('gpt-5')
            ) || null;
        } else if (preferredModel === 'claude-opus') {
            // Look for Claude Opus
            selectedModel = models.find(m =>
                m.name.toLowerCase().includes('claude') &&
                m.name.toLowerCase().includes('opus')
            ) || models.find(m =>
                m.name.toLowerCase().includes('claude')
            ) || null;
        }

        // Fallback to first available model
        if (!selectedModel && models.length > 0) {
            console.log(`Preferred model "${preferredModel}" not found, using first available: ${models[0].name}`);
            selectedModel = models[0];
        }

        if (selectedModel) {
            console.log(`Selected model: ${selectedModel.name} (vendor: ${selectedModel.vendor})`);
        } else {
            console.log('No suitable model found');
        }

        return selectedModel;

    } catch (error) {
        console.error('Error getting Copilot model:', error);
        return null;
    }
}

/**
 * Parse HTTP request body
 */
function parseRequestBody(req: http.IncomingMessage): Promise<any> {
    return new Promise((resolve, reject) => {
        let body = '';

        req.on('data', (chunk) => {
            body += chunk.toString();
        });

        req.on('end', () => {
            try {
                const parsed = JSON.parse(body);
                resolve(parsed);
            } catch (error) {
                reject(new Error('Invalid JSON in request body'));
            }
        });

        req.on('error', (error) => {
            reject(error);
        });
    });
}
