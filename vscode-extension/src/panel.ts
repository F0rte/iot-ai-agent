import * as vscode from 'vscode';

export class AgentPanel {
    public static currentPanel: AgentPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    static createOrShow(extensionUri: vscode.Uri) {
        if (AgentPanel.currentPanel) {
            AgentPanel.currentPanel._panel.reveal(vscode.ViewColumn.One);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'agentController',
            'Agent Controller',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );
        AgentPanel.currentPanel = new AgentPanel(panel);
    }

    private constructor(panel: vscode.WebviewPanel) {
        this._panel = panel;
        this._panel.webview.html = this._getHtmlContent();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    private _getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src http://localhost:8000;">
    <title>Agent Controller</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            padding: 16px;
            margin: 0;
        }
        h2 { margin-top: 0; }
        #status {
            font-size: 0.9em;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 16px;
        }
        #events { list-style: none; padding: 0; margin: 0; }
        .event-item {
            background: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 4px;
            padding: 10px 12px;
            margin-bottom: 8px;
        }
        .event-item.iot   { border-left: 3px solid #4ec9b0; }
        .event-item.agent { border-left: 3px solid #dcdcaa; }
        .event-item.error { border-left: 3px solid #f44747; }
        .label {
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
            margin-bottom: 6px;
            opacity: 0.7;
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-all;
            font-family: var(--vscode-editor-font-family);
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <h2>🤖 Agent Controller</h2>
    <div id="status">⏳ ai-agent に接続中 (localhost:8000)...</div>
    <ul id="events"></ul>
    <script>
        const statusEl = document.getElementById('status');
        const eventsEl = document.getElementById('events');
        const MAX_ITEMS = 50;

        function escapeHtml(str) {
            return str
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }

        function addEvent(type, content) {
            const labels = { iot: '📡 IoT 受信', agent: '🤖 エージェント応答', error: '❌ エラー' };
            const li = document.createElement('li');
            li.className = 'event-item ' + type;
            const text = type === 'agent'
                ? content.response
                : JSON.stringify(type === 'iot' ? content.data : content, null, 2);
            li.innerHTML =
                '<div class="label">' + (labels[type] || type) + '</div>' +
                '<pre>' + escapeHtml(text) + '</pre>';
            eventsEl.insertBefore(li, eventsEl.firstChild);
            while (eventsEl.children.length > MAX_ITEMS) {
                eventsEl.removeChild(eventsEl.lastChild);
            }
        }

        function connect() {
            const es = new EventSource('http://localhost:8000/events');
            es.onopen = () => {
                statusEl.textContent = '✅ ai-agent に接続済み (localhost:8000)';
            };
            es.onmessage = (e) => {
                try {
                    const event = JSON.parse(e.data);
                    if (event.type === 'ping') return;
                    addEvent(event.type, event);
                } catch (_) {}
            };
            es.onerror = () => {
                statusEl.textContent = '❌ ai-agent に接続できません — 5秒後に再試行';
                es.close();
                setTimeout(connect, 5000);
            };
        }

        connect();
    </script>
</body>
</html>`;
    }

    dispose() {
        AgentPanel.currentPanel = undefined;
        this._panel.dispose();
        this._disposables.forEach(d => d.dispose());
        this._disposables = [];
    }
}
