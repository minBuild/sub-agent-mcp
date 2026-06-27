import os
import subprocess

from tools.store import read_session, write_session, session_path


def _as_escape(text: str) -> str:
    """AppleScript 문자열 리터럴 안전화(역슬래시/큰따옴표)."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


async def send_message(session_id: str, message: str) -> str:
    """
    대기 중인 자식 세션에게 추가 지시를 전달.
    ⚠️ message는 '한 줄'을 권장한다. iTerm write text는 개행을 Enter로 보내므로,
       여러 줄 메시지는 줄마다 따로 제출될 수 있다.
    """
    if not os.path.exists(session_path(session_id)):
        return f"[시스템 에러] 세션 파일이 없습니다: {session_id}"

    data = read_session(session_id)
    if data is None:
        return f"[시스템 에러] 세션 {session_id} 파일을 읽지 못했습니다."

    iterm_id = data.get("iterm_id")
    if not iterm_id:
        return f"[시스템 에러] 해당 세션의 iTerm2 고유 ID 정보를 찾을 수 없습니다."

    safe_message = _as_escape(message)

    applescript = f'''
    tell application "iTerm"
        set sessionFound to false

        repeat with w in windows
            repeat with t in tabs of w
                repeat with s in sessions of t
                    if id of s is "{iterm_id}" then
                        set sessionFound to true
                        tell s
                            write text "{safe_message}"
                            delay 0.5
                            write text ""
                        end tell
                        exit repeat
                    end if
                end repeat
                if sessionFound then exit repeat
            end repeat
            if sessionFound then exit repeat
        end repeat

        if not sessionFound then
            return "SESSION_NOT_FOUND"
        end if
    end tell
    '''

    result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)

    if "SESSION_NOT_FOUND" in result.stdout or result.returncode != 0:
        return f"[시스템 에러] ID [{session_id}]에 해당하는 iTerm2 탭을 찾을 수 없습니다."

    # 릴레이 지시를 보냈으니 다시 RUNNING으로 표시
    data["status"] = "RUNNING"
    write_session(session_id, data)

    return f"[시스템] 세션 {session_id} 탭에 추가 지시('{message}') 전달 완료."
