from langchain_core.tools import tool
import os

# センサー種別ごとのインメモリ履歴
_history: dict[str, list[dict]] = {}

# センサー種別ごとの異常検知閾値
_ANOMALY_THRESHOLDS: dict[str, dict[str, tuple[float, float]]] = {
    "heart_rate": {
        "heart_rate": (40.0, 180.0),
        "bpm": (40.0, 180.0),
    },
    "motion": {
        # 合成加速度の正常範囲（g単位）
        "acceleration_magnitude": (0.0, 20.0),
    },
}

# ファイル操作ツールが参照するワークスペースルート
_workspace_root: str = ""

# 走行中フラグ（notify_start/stop から更新、dev_graph から参照）
_is_running: bool = False

# IoTデバイスのステータス（デバイスID -> ステータス情報の辞書）
_iot_status: dict[str, dict] = {}


def set_workspace_root(path: str) -> None:
    global _workspace_root
    _workspace_root = path


def set_is_running(value: bool) -> None:
    global _is_running
    _is_running = value


def get_is_running() -> bool:
    return _is_running


def set_iot_status(device_id: str, status: dict) -> None:
    """IoTデバイスのステータスを設定する。
    
    Args:
        device_id: デバイスID（例: "device_001", "sensor_heart_rate"）
        status: ステータス情報（辞書形式）
    """
    global _iot_status
    _iot_status[device_id] = status


def get_iot_status(device_id: str | None = None) -> dict | None:
    """IoTデバイスのステータスを取得する。
    
    Args:
        device_id: デバイスID。Noneの場合は全デバイスのステータスを返す。
    
    Returns:
        device_idが指定された場合は該当デバイスのステータス（存在しない場合はNone）
        device_idがNoneの場合は全デバイスのステータス辞書
    """
    if device_id is None:
        return _iot_status.copy()
    return _iot_status.get(device_id)


def _resolve(path: str) -> str:
    """相対パスをワークスペースルートからの絶対パスに変換する"""
    if os.path.isabs(path):
        return path
    if not _workspace_root:
        return path
    return os.path.join(_workspace_root, path)


@tool
def save_record(sensor_type: str, data: dict) -> str:
    """センサーデータをメモリに保存する。

    Args:
        sensor_type: センサー種別（例: heart_rate, motion, unknown）
        data: 保存するセンサーデータ
    """
    if sensor_type not in _history:
        _history[sensor_type] = []
    _history[sensor_type].append(data)
    return f"{sensor_type} のデータを保存しました（累計: {len(_history[sensor_type])} 件）"


@tool
def get_history(sensor_type: str, n: int = 5) -> list[dict]:
    """指定センサーの直近n件の履歴データを取得する。

    Args:
        sensor_type: センサー種別（例: heart_rate, motion, unknown）
        n: 取得件数（デフォルト: 5）
    """
    records = _history.get(sensor_type, [])
    return records[-n:]


@tool
def detect_anomaly(sensor_type: str, data: dict) -> str:
    """センサーデータの異常を閾値ベースで検知する。

    Args:
        sensor_type: センサー種別（例: heart_rate, motion）
        data: チェックするセンサーデータ
    """
    thresholds = _ANOMALY_THRESHOLDS.get(sensor_type, {})
    anomalies = []

    for key, (low, high) in thresholds.items():
        value = data.get(key)
        if value is not None and not (low <= float(value) <= high):
            anomalies.append(f"{key}={value} が正常範囲({low}〜{high})を外れています")

    if anomalies:
        return "⚠️ 異常検知: " + ", ".join(anomalies)
    return "✅ 正常範囲内です"


TOOLS = [save_record, get_history, detect_anomaly]


@tool
def read_file(path: str) -> str:
    """ワークスペース内のファイルを読み込む。

    Args:
        path: ワークスペースルートからの相対パス（例: docs/plan.md）
    """
    full_path = _resolve(path)
    if not os.path.exists(full_path):
        return f"エラー: ファイルが見つかりません: {path}"
    with open(full_path, encoding="utf-8") as f:
        return f.read()


@tool
def read_file_lines(path: str, start_line: int, end_line: int) -> str:
    """ワークスペース内のファイルを指定行範囲だけ読み込む（トークン節約用）。

    Args:
        path: ワークスペースルートからの相対パス（例: src/main.py）
        start_line: 読み始める行番号（1始まり）
        end_line: 読み終わる行番号（inclusive）
    """
    full_path = _resolve(path)
    if not os.path.exists(full_path):
        return f"エラー: ファイルが見つかりません: {path}"
    with open(full_path, encoding="utf-8") as f:
        lines = f.readlines()
    total = len(lines)
    s = max(0, start_line - 1)
    e = min(total, end_line)
    selected = lines[s:e]
    header = f"[{path} 行 {s+1}〜{e} / 全{total}行]\n"
    return header + "".join(selected)


@tool
def write_file(path: str, content: str) -> str:
    """ワークスペース内のファイルを書き込む（新規作成・上書き）。

    Args:
        path: ワークスペースルートからの相対パス（例: src/main.py）
        content: 書き込む内容
    """
    full_path = _resolve(path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True) if os.path.dirname(full_path) else None
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ ファイルを書き込みました: {path}"


@tool
def list_files(directory: str = ".") -> str:
    """ワークスペース内のディレクトリのファイル一覧を取得する。

    Args:
        directory: ワークスペースルートからの相対パス（デフォルト: ワークスペースルート）
    """
    full_path = _resolve(directory)
    if not os.path.exists(full_path):
        return f"エラー: ディレクトリが見つかりません: {directory}"
    entries = []
    for root, dirs, files in os.walk(full_path):
        # 隠しディレクトリ・__pycache__ をスキップ
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        rel_root = os.path.relpath(root, full_path)
        for file in files:
            if not file.startswith("."):
                entry = file if rel_root == "." else f"{rel_root}/{file}"
                entries.append(entry)
    return "\n".join(entries) if entries else "（ファイルなし）"


@tool
def run_shell(command: str, cwd: str = ".") -> str:
    """ワークスペース内でシェルコマンドを実行する。

    Args:
        command: 実行するコマンド（例: "uv run python test.py", "npm test"）
        cwd: 実行ディレクトリ（ワークスペースルートからの相対パス、デフォルト: ルート）
    """
    import subprocess

    full_cwd = _resolve(cwd)

    # セキュリティ: ワークスペース外へのアクセスを防止
    if _workspace_root and not full_cwd.startswith(_workspace_root):
        return f"エラー: ワークスペース外のディレクトリ: {cwd}"

    # セキュリティ: 危険なコマンドをブロック
    dangerous_patterns = [
        "rm -rf /",
        "sudo ",
        "mkfs",
        "> /dev/",
        "dd if=",
        ":(){ :|:& };:",  # fork bomb
    ]
    if any(pattern in command for pattern in dangerous_patterns):
        return f"エラー: 危険なコマンドが検出されました: {command[:50]}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=full_cwd,
            capture_output=True,
            text=True,
            timeout=60,  # 60秒タイムアウト
        )

        output = f"=== コマンド ===\n{command}\n\n"
        output += f"=== stdout ===\n{result.stdout}\n"
        if result.stderr:
            output += f"\n=== stderr ===\n{result.stderr}\n"
        output += f"\n終了コード: {result.returncode}"

        return output

    except subprocess.TimeoutExpired:
        return f"エラー: コマンドがタイムアウトしました（60秒）: {command}"
    except Exception as e:
        return f"エラー: コマンド実行失敗: {e}"


FILE_TOOLS = [read_file, read_file_lines, write_file, list_files, run_shell]
ALL_TOOLS = TOOLS + FILE_TOOLS
