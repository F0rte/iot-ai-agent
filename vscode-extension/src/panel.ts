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
      'RunCode',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
      }
    );

    AgentPanel.currentPanel = new AgentPanel(panel, extensionUri);
  }

  private readonly _extensionUri: vscode.Uri;

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    this._extensionUri = extensionUri;
    this._panel.webview.html = this._getHtmlContent();
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
  }

  public dispose() {
    AgentPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) {
        x.dispose();
      }
    }
  }

  private _getHtmlContent(): string {
    const rabbitUri = this._panel.webview.asWebviewUri(
      vscode.Uri.joinPath(this._extensionUri, 'media', 'rabbit2.png')
    );
    return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none';
                img-src ${this._panel.webview.cspSource} data:;
                 img-src data:;
                 style-src 'unsafe-inline';
                 script-src 'unsafe-inline';
                 connect-src http://localhost:8000;">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI CONTROLLER</title>
  <style>
    :root{
      --bg:#0a0f1a;
      --panel: rgba(255,255,255,0.04);
      --panel2: rgba(255,255,255,0.06);
      --stroke: rgba(255,255,255,0.10);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.60);

      --blue:#2f7fff;
      --green:#2ee59d;
      --yellow:#ffd34d;
      --red:#ff5b5b;
      --cyan:#48e6ff;

      --radius: 14px;
      --shadow: 0 10px 30px rgba(0,0,0,0.38);
    }

    *{ box-sizing:border-box; }
    body{
      margin:0;
      color:var(--text);
      background:
        radial-gradient(1200px 800px at 15% 0%, rgba(47,127,255,0.18), transparent 55%),
        radial-gradient(900px 700px at 85% 20%, rgba(46,229,157,0.10), transparent 60%),
        var(--bg);
      font-family: var(--vscode-font-family, system-ui);
    }

    .wrap{
      height:100vh;
      display:flex;
      flex-direction:column;
      padding: 10px;
      gap: 10px;
    }

    /* Top bar */
    .topbar{
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding: 10px 12px;
      border-radius: var(--radius);
      border: 1px solid var(--stroke);
      background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
      box-shadow: var(--shadow);
    }
    .brand{
      display:flex;
      align-items:center;
      gap: 10px;
      font-weight: 900;
      letter-spacing: 0.3px;
    }
    .chipIcon{
      width: 28px; height: 28px;
      border-radius: 10px;
      display:grid;
      place-items:center;
      background: rgba(47,127,255,0.14);
      border: 1px solid rgba(47,127,255,0.30);
      color: var(--cyan);
      font-weight: 900;
      font-size: 12px;
    }
    .rightIcons{
      display:flex;
      align-items:center;
      gap: 10px;
      color: var(--muted);
      user-select:none;
    }
    .iconBtn{
      width: 28px; height: 28px;
      border-radius: 10px;
      display:grid;
      place-items:center;
      border: 1px solid rgba(255,255,255,0.10);
      background: rgba(255,255,255,0.03);
      cursor:pointer;
    }

    /* Status pills */
    .pills{
      display:flex;
      gap: 8px;
      flex-wrap:wrap;
    }
    .pill{
      display:inline-flex;
      align-items:center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.03);
      font-size: 12px;
      color: var(--muted);
    }
    .dot{ width: 8px; height: 8px; border-radius: 999px; background: rgba(255,255,255,0.25); }
    .pill.ok .dot{ background: var(--green); }
    .pill.warn .dot{ background: var(--yellow); }
    .pill.bad .dot{ background: var(--red); }

    /* Controls row */
    .controls{
      display:grid;
      grid-template-columns: 1fr 1fr 1.6fr;
      gap: 10px;
    }
    .btn{
      padding: 12px 12px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      font-weight: 900;
      cursor:pointer;
      text-align:center;
      user-select:none;
    }
    .btn.primary{
      border-color: rgba(47,127,255,0.35);
      background: rgba(47,127,255,0.18);
    }
    .btn:active{ transform: translateY(1px); }

    .select{
      padding: 12px 12px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.18);
      color: var(--text);
      outline:none;
      font-weight: 800;
      width:100%;
    }

    /* ウサギ用のアニメーションカード */
    .rabbit-card {
      height: 100px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255,255,255,0.04);
      border-radius: var(--radius);
      border: 1px solid var(--stroke);
      overflow: hidden;
      position: relative;
      box-shadow: var(--shadow);
    }

    .rabbit {
      width: 85px; /* 1コマの幅 (510 / 6) */
      height: 82px;
      background: url('${rabbitUri}') no-repeat;
      background-size: 510px 82px;
      background-position: 32px 0;
      /* --speed 変数で速度を外部から制御 */
      animation: run var(--speed, 0.8s) steps(6) infinite;
    }

    @keyframes run {
      from { background-position: 32 0; }
      to { background-position: -510px 0; }
    }

    .speed-label {
      position: absolute;
      bottom: 8px;
      right: 12px;
      font-size: 10px;
      color: var(--cyan);
      font-family: monospace;
      font-weight: 800;
    }

    /* Main content */
    .content{
      flex:1;
      overflow:auto;
      padding: 8px 6px;
    }
    .md{
      padding: 12px 12px 16px;
      border-radius: var(--radius);
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(0,0,0,0.14);
      line-height: 1.7;
      color: rgba(255,255,255,0.86);
      white-space: pre-wrap;
      word-break: break-word;
    }
    .md h2,.md h3{
      margin: 10px 0 8px;
      color: rgba(120,200,255,0.95);
    }
    .md ul{ margin: 6px 0 10px 18px; }
    .md li{ margin: 4px 0; }

    /* Bottom prompt */
    .promptBar{
      border-radius: var(--radius);
      border: 1px solid rgba(255,255,255,0.10);
      background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
      box-shadow: var(--shadow);
      padding: 10px;
    }
    .promptHd{
      display:flex;
      align-items:center;
      justify-content:space-between;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }
    .promptRow{
      display:grid;
      grid-template-columns: 1fr 44px 44px;
      gap: 8px;
      align-items:end;
    }
    textarea{
      width:100%;
      min-height: 78px;
      resize:none;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.18);
      color: var(--text);
      outline:none;
      line-height: 1.5;
    }
    .miniBtn{
      width: 44px; height: 44px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.04);
      cursor:pointer;
      display:grid;
      place-items:center;
      font-weight: 950;
      color: rgba(255,255,255,0.90);
      user-select:none;
    }
    .miniBtn.primary{
      border-color: rgba(47,127,255,0.35);
      background: rgba(47,127,255,0.18);
    }
  </style>
</head>

<body>
  <div class="wrap">
    <!-- Top bar -->
    <div class="topbar">
      <div class="brand">
        <div class="chipIcon">⌁</div>
        <div>AI CONTROLLER</div>
      </div>

      <div class="rightIcons">
        <div class="iconBtn" title="Refresh">⟳</div>
        <div class="iconBtn" title="Settings">⚙</div>
      </div>
    </div>

    <!-- Status pills -->
    <div class="pills">
      <div id="pillMock" class="pill warn"><span class="dot"></span><span>モック表示中</span></div>
      <div id="pillOk" class="pill ok"><span class="dot"></span><span>ai-agent 接続済み</span></div>
      <div id="pillNg" class="pill bad"><span class="dot"></span><span>未接続</span></div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <div id="btnRun" class="btn primary">RUN</div>
      <div id="btnSleep" class="btn">SLEEP</div>
      <select id="model" class="select">
        <option>Gemini Pro</option>
        <option>GPT-4.1</option>
        <option>Local LLM</option>
      </select>
    </div>

    <!-- rabbit-card -->
      <div class="rabbit-card">
        <div id="rabbitSprite" class="rabbit"></div>
        <div class="speed-label">CLK: <span id="speedVal">0</span> MHz</div>
    </div>

    <!-- Content -->
    <div class="content">
      <div id="md" class="md"></div>
    </div>

    <!-- Prompt -->
    <div class="promptBar">
      <div class="promptHd">
        <div>PROMPT / SPECIFICATION</div>
        <div style="text-transform:none;">Markdown supported</div>
      </div>
      <div class="promptRow">
        <textarea id="prompt" placeholder="Project: ...&#10;Goal: ...&#10;Constraints: ..."></textarea>
        <div class="miniBtn" id="btnAttach" title="Attach">📎</div>
        <div class="miniBtn primary" id="btnSend" title="Send">▶</div>
      </div>
    </div>
  </div>

  <script>
    // ---------- status pills ----------
    const pillMock = document.getElementById("pillMock");
    const pillOk = document.getElementById("pillOk");
    const pillNg = document.getElementById("pillNg");

    const STATUS = { MOCK:"mock", CONNECTED:"connected", DISCONNECTED:"disconnected" };
    function setPills(mode){
      pillMock.style.opacity = (mode===STATUS.MOCK) ? "1" : "0.35";
      pillOk.style.opacity   = (mode===STATUS.CONNECTED) ? "1" : "0.35";
      pillNg.style.opacity   = (mode===STATUS.DISCONNECTED) ? "1" : "0.35";
    }

    // ---------- markdown-ish view ----------
    const mdEl = document.getElementById("md");

    function setMarkdown(text){
      // ここは簡易。必要なら後で markdown パーサに差し替え（今はフロントだけ）
      mdEl.textContent = text;
    }

    // 初期文面（スクショ寄せ）
    setMarkdown(
      "## エージェントの自律動作\\n\\n" +
      "エージェントが自律的に動作しました\\n\\n" +
      "## 詳細\\n\\n" +
      "このファイルは、自律開発エージェントによって自動的に生成されました。\\n" +
      "エージェントは以下の処理を実行しました：\\n\\n" +
      "- プロジェクト構造の確認\\n" +
      "- Markdownファイルの作成\\n" +
      "- 指定された内容の書き込み\\n\\n" +
      "## 実行日時\\n\\n" +
      "このファイルは自律エージェントによって作成されました。"
    );

    // ---------- mock + connect ----------
    const mockEvents = [
      { type: "iot", data: { sensor: "heart_rate", value: 80, unit: "bpm" } },
      { type: "agent", response: "心拍数80bpmは正常範囲内です。" },
      { type: "iot", data: { sensor: "hardware_clock", value: 450, unit: "MHz" } },
      { type: "agent", response: "温度スパイクの検出ロジックを有効化しました。" }
    ];

    let mockTimer = null;
    let idx = 0;

function applyEvent(ev){
      if(!ev || ev.type === "ping") return;

      if(ev.type === "agent"){
        setMarkdown(
          "## エージェント応答\n\n" +
          (ev.response || "（応答なし）") + "\n\n" +
          "## 詳細\n\n" +
          "- 状態更新を反映しました\n" +
          "- 追加の指示を入力できます"
        );
        return;
      }

      // --- ここをウサギ用に修正 ---
      if(ev.type === "iot"){
        const d = ev.data || {};
        if(d.sensor === "hardware_clock"){
          const val = d.value ?? 0;
          
          // 数値を画面に表示
          const speedValEl = document.getElementById("speedVal");
          if(speedValEl) speedValEl.textContent = String(val);

          // アニメーション速度の計算
          // valが大きくなるとduration（1周の秒数）が小さくなり、速く走ります
          // 例: 450MHz のとき 400/450 ≒ 0.88秒
          const rabbit = document.getElementById("rabbitSprite");
          if(rabbit) {
            const duration = Math.max(0.1, 400 / (val + 1)); 
            rabbit.style.setProperty('--speed', duration + 's');
          }
        }
        return;
      }
    }

      if(ev.type === "iot"){
        const d = ev.data || {};
        if(d.sensor === "hardware_clock"){
          document.getElementById("clockValue").textContent = String(d.value ?? 450);
        }
        return;
      }
    }

    function startMock(){
      if(mockTimer) return;
      setPills(STATUS.MOCK);
      applyEvent(mockEvents[idx++ % mockEvents.length]);
      mockTimer = setInterval(function(){
        applyEvent(mockEvents[idx++ % mockEvents.length]);
      }, 1800);
    }

    function stopMock(){
      if(!mockTimer) return;
      clearInterval(mockTimer);
      mockTimer = null;
    }

    function connect(){
      setPills(STATUS.DISCONNECTED);
      const es = new EventSource("http://localhost:8000/events");

      es.onopen = function(){
        stopMock();
        setPills(STATUS.CONNECTED);
      };

      es.onmessage = function(e){
        try{
          const ev = JSON.parse(e.data);
          applyEvent(ev);
        }catch(_){}
      };

      es.onerror = function(){
        setPills(STATUS.DISCONNECTED);
        startMock();
        es.close();
        setTimeout(connect, 5000);
      };
    }

    connect();

    // ---------- controls (UI only for now) ----------
    document.getElementById("btnRun").addEventListener("click", function(){
      applyEvent({ type:"agent", response:"RUN を押しました。タスクを開始します。" });
    });
    document.getElementById("btnSleep").addEventListener("click", function(){
      applyEvent({ type:"agent", response:"SLEEP を押しました。待機モードにします。" });
    });

    // send (backendがあるなら /command に投げる)
    const promptEl = document.getElementById("prompt");
    document.getElementById("btnSend").addEventListener("click", async function(){
      const text = (promptEl.value || "").trim();
      if(!text) return;

      // まずはローカル反映（デモ）
      applyEvent({ type:"agent", response:"受信: \\n" + text });

      // 本番投げる場合（エンドポイントがあるなら）
      try{
        await fetch("http://localhost:8000/command", {
          method:"POST",
          headers:{ "Content-Type":"application/json" },
          body: JSON.stringify({ command: text })
        });
      }catch(_){}
    });
  </script>
</body>
</html>`;
  }
}