import os
import subprocess

from sam_config import INBOX_DIR
from tools.store import read_session, session_path


async def close_session(session_id: str) -> str:
    """
    작업이 끝난 세션의 iTerm2 탭을 종료하고 인박스 관련 파일을 정리한다.
    ⚠️ 현재는 파일을 '삭제'한다. 끝난 세션을 보관하려면 삭제 대신
       아카이브 디렉토리로 옮기는 방식으로 확장할 수 있다.
    """
    path = session_path(session_id)
    if not os.path.exists(path):
        return f"[시스템 에러] 세션 파일이 없습니다: {session_id}"

    data = read_session(session_id)
    iterm_id = (data or {}).get("iterm_id")

    tab_closed = False
    if iterm_id:
        applescript = f'''
        tell application "iTerm"
            set sessionFound to false
            repeat with w in windows
                repeat with t in tabs of w
                    repeat with s in sessions of t
                        if id of s is "{iterm_id}" then
                            set sessionFound to true
                            tell t to close
                            exit repeat
                        end if
                    end repeat
                    if sessionFound then exit repeat
                end repeat
                if sessionFound then exit repeat
            end repeat
            if sessionFound then
                return "CLOSED"
            else
                return "TAB_NOT_FOUND"
            end if
        end tell
        '''
        result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
        tab_closed = "CLOSED" in result.stdout

    # 세션 관련 파일 일괄 정리(JSON + context.md + prompt.md + 혹시 남은 .tmp)
    for fname in (
        f"{session_id}.json",
        f"{session_id}.json.tmp",
        f"{session_id}_context.md",
        f"{session_id}_prompt.md",
    ):
        fpath = os.path.join(INBOX_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    if iterm_id and not tab_closed:
        return f"[시스템] 세션 {session_id} 파일은 정리했으나, iTerm2 탭은 못 찾았습니다(이미 닫혔을 수 있음)."
    return f"[시스템] 세션 {session_id}이(가) 종료되었습니다."
