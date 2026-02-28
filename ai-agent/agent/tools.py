from langchain_core.tools import tool

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
