import os
import json
import time

from sam_config import INBOX_DIR


def session_path(session_id: str) -> str:
    """세션 JSON 파일 경로를 반환."""
    return os.path.join(INBOX_DIR, f"{session_id}.json")


def read_session(session_id: str, retries: int = 3, delay: float = 0.05):
    """
    세션 JSON을 안전하게 읽는다.
    자식이 파일을 '쓰는 도중'에 읽으면 JSONDecodeError가 날 수 있으므로 몇 번 재시도한다.
    파일이 없으면 None, 끝까지 깨져 있으면 마지막 예외를 올린다.
    """
    path = session_path(session_id)
    if not os.path.exists(path):
        return None

    last_err = None
    for attempt in range(retries):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
    raise last_err


def write_session(session_id: str, data: dict) -> None:
    """
    세션 JSON을 '원자적'으로 쓴다.
    임시 파일에 다 쓴 뒤 os.replace로 갈아끼우므로, 쓰기 도중 크래시해도
    원본이 반쯤 깨진 채로 남지 않는다(폴링 측의 JSONDecodeError 예방).
    """
    path = session_path(session_id)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
