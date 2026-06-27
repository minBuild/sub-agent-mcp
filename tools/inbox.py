import os
from datetime import datetime, timezone, timedelta

from sam_config import STALE_MINUTES
from tools.store import read_session, session_path

KST = timezone(timedelta(hours=9))


def _age_minutes(created_at: str):
    """created_at(ISO8601) 기준 경과 분. 파싱 실패 시 None."""
    try:
        started = datetime.fromisoformat(created_at)
        return (datetime.now(KST) - started).total_seconds() / 60
    except Exception:
        return None


async def check_inbox(session_ids: list[str]) -> str:
    """
    생성된 자식 세션들의 완료 여부를 폴링하여 결과를 수집합니다.
    """
    report = []
    success = 0      # 결과 보고가 들어온 세션 수
    pending = 0      # 아직 실행 중(또는 읽기 중)인 세션 수

    for sid in session_ids:
        if not os.path.exists(session_path(sid)):
            report.append(f"- 세션 {sid}: 존재하지 않음 (이미 close됐거나 잘못된 ID)")
            continue

        try:
            data = read_session(sid)
        except Exception as e:
            # 자식이 파일을 쓰는 중일 수 있다 -> 아직 진행 중으로 간주
            pending += 1
            report.append(f"- 세션 {sid}: 읽기 일시 실패(쓰기 중일 수 있음) - {e}")
            continue

        status = data.get("status", "UNKNOWN")

        if status == "SUCCESS":
            success += 1
            report.append(f"=== [성공] 세션 {sid} 결과 ===\n{data.get('result', '(결과 없음)')}\n")
        elif status == "SPAWN_FAILED":
            report.append(f"- 세션 {sid}: ⚠️ 생성 실패(SPAWN_FAILED) - 탭이 안 떴습니다.")
        else:
            pending += 1
            age = _age_minutes(data.get("created_at", ""))
            stale = ""
            if age is not None and age > STALE_MINUTES:
                stale = f" ⚠️ {int(age)}분째 무응답(부모/자식이 죽었을 수 있음)"
            report.append(f"- 세션 {sid}: 아직 실행 중... (상태: {status}){stale}")

    if pending == 0 and success > 0:
        header = "🎉 요청한 세션의 작업이 모두 완료되었습니다!"
    elif pending == 0:
        header = "ℹ️ 진행 중인 세션이 없습니다(완료/실패/미존재만 있음)."
    else:
        header = "⏳ 일부 세션이 아직 작업 중입니다. 잠시 후 다시 check_inbox를 해주세요."

    return header + "\n\n" + "\n".join(report)
