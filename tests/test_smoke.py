"""
SAM 스모크 테스트 - iTerm/AppleScript 없이 핵심 로직만 검증한다.

실행:
    python tests/test_smoke.py        # 의존성 없이 (권장)
    python -m pytest tests/ -v        # pytest 가 깔려 있으면

핵심 검증 포인트:
  1. 세션 JSON 원자적 쓰기/읽기 라운드트립
  2. delegate_to_sam 이 위험한 task 를 AppleScript 로 흘리지 않음 (인젝션 차단)
  3. check_inbox 가 구 스키마/누락 필드/없는 세션에도 안 깨짐
"""
import os
import sys
import atexit
import shutil
import asyncio
import tempfile

# 프로젝트 루트를 import 경로에 추가하고, 테스트 전용 임시 인박스를 쓰도록 SAM_HOME 지정.
# (sam_config 가 import 시점에 SAM_HOME 을 읽으므로 import 전에 설정해야 한다)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
_TMP = tempfile.mkdtemp(prefix="sam-test-")
os.environ["SAM_HOME"] = _TMP
atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))  # 끝나면 임시 인박스 정리

from tools import store          # noqa: E402
import tools.delegate as delegate  # noqa: E402
from tools.inbox import check_inbox  # noqa: E402


def test_store_round_trip():
    """원자적 쓰기 후 그대로 다시 읽혀야 한다."""
    store.write_session("rt1", {"session_id": "rt1", "status": "RUNNING", "task": "t"})
    data = store.read_session("rt1")
    assert data is not None
    assert data["status"] == "RUNNING"
    assert data["task"] == "t"
    # 없는 세션은 None
    assert store.read_session("does-not-exist") is None


def test_delegate_does_not_leak_task_into_applescript(monkeypatch=None):
    """따옴표/개행/백틱이 든 task 가 AppleScript 스크립트 본문에 새지 않아야 한다."""
    captured = {}

    def fake_run(args, **kwargs):
        captured["script"] = args[-1]

        class _R:
            returncode = 0
            stdout = "fake-iterm-id\n"
            stderr = ""
        return _R()

    delegate.subprocess.run = fake_run  # iTerm 안 띄우고 가로챔

    nasty = 'rm -rf /; echo "x" `whoami`\nSECOND LINE injection'
    res = asyncio.run(delegate.delegate_to_sam(nasty, working_dir=_ROOT))
    assert "생성 성공" in res

    script = captured["script"]
    assert "rm -rf" not in script, "task 내용이 AppleScript 로 샜다!"
    assert "SECOND LINE" not in script, "개행 뒤 내용이 샜다!"
    assert "_prompt.md" in script, "자식에겐 프롬프트 파일을 가리키는 한 줄만 가야 한다"


def test_check_inbox_survives_messy_input():
    """구 스키마(필드 누락), 없는 세션이 섞여도 예외 없이 처리돼야 한다."""
    store.write_session("old", {"session_id": "old", "status": "RUNNING"})  # result/created_at 없음
    store.write_session("ok", {"session_id": "ok", "status": "SUCCESS", "result": "done"})

    out = asyncio.run(check_inbox(["old", "ok", "missing"]))
    assert "missing" in out and "존재하지 않음" in out
    assert "done" in out          # 성공 결과는 표시
    assert "아직 실행 중" in out    # 미완료도 표시 (KeyError 없이)


def _run_standalone():
    tests = [
        test_store_round_trip,
        test_delegate_does_not_leak_task_into_applescript,
        test_check_inbox_survives_messy_input,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n{'전부 통과 🎉' if failed == 0 else f'{failed}개 실패'}")
    return failed


if __name__ == "__main__":
    print("SAM 스모크 테스트")
    sys.exit(1 if _run_standalone() else 0)
