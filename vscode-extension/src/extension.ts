import * as vscode from 'vscode';
import { AgentPanel } from './panel';

export function activate(context: vscode.ExtensionContext) {
    console.log('AgentController extension activated');

    context.subscriptions.push(
        vscode.commands.registerCommand('agentController.openPanel', () => {
            AgentPanel.createOrShow(context.extensionUri);
        })
    );
}

export function deactivate() {}
