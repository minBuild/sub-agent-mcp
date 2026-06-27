import os
from datetime import datetime, timezone, timedelta

from tools.store import read_session, write_session, session_path

KST = timezone(timedelta(hours=9))


async def report_result(session_id: str, result: str, summary: str = "") -> str:
    """
    자식 에이전트가 작업 완료 후 부모에게 결과를 구조화해서 보고.
    summary(선택): 한 줄 요약. 나중에 세션 검색/이어하기 품질을 높여준다.
    """
    if not os.path.exists(session_path(session_id)):
        return f"[에러] 존재하지 않는 세션 ID: {session_id}"

    data = read_session(session_id)
    if data is None:
        return f"[에러] 세션 {session_id} 파일을 읽지 못했습니다."

    data["status"] = "SUCCESS"
    data["result"] = result
    data["closed_at"] = datetime.now(KST).isoformat()
    if summary:
        data["summary"] = summary

    write_session(session_id, data)

    return f"[시스템] 세션 {session_id}의 보고가 인박스에 정상 접수."
