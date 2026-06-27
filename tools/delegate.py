import os
import uuid
import subprocess
from datetime import datetime, timezone, timedelta

from sam_config import (
    INBOX_DIR, CURRENT_DIR, ENV_PREFIX, BOOT_DELAY, PROMPT_DELAY,
    PERMISSION_MODE, ALLOWED_TOOLS,
)
from tools.store import write_session

KST = timezone(timedelta(hours=9))


def _git_branch(cwd: str) -> str:
    """해당 디렉토리의 git 브랜치명을 반환(없으면 빈 문자열). 검색/이어하기용 메타데이터."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _as_escape(text: str) -> str:
    """AppleScript 문자열 리터럴 안전화(역슬래시/큰따옴표). 호출부에서 개행은 없도록 보장한다."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _sh_single_quote(path: str) -> str:
    """쉘 작은따옴표 안에 안전하게 넣기 위해 내부 작은따옴표를 escape."""
    return path.replace("'", "'\\''")


async def delegate_to_sam(task: str, rag_context: str = "", working_dir: str = "") -> str:
    """
    독립된 AI 자식 세션(SAM)을 iTerm2 새 탭에 생성하고 작업을 위임한 뒤 고유 세션 ID를 반환.
    working_dir 를 주면 그 디렉토리에서 자식을 실행한다(기본값: 서버 기동 디렉토리 CURRENT_DIR).
    """
    session_id = str(uuid.uuid4())[:8]

    # 1. 자식이 실제로 일할 디렉토리 결정 + 검증
    cwd = os.path.abspath(os.path.expanduser(working_dir)) if working_dir else CURRENT_DIR
    if not os.path.isdir(cwd):
        return f"[시스템 에러] 작업 디렉토리가 존재하지 않습니다: {cwd}"

    # 2. 인박스에 세션 상태 파일 생성(메타데이터 포함, 원자적 쓰기)
    session_data = {
        "session_id": session_id,
        "status": "RUNNING",
        "task": task,
        "result": "",
        "iterm_id": "",
        "created_at": datetime.now(KST).isoformat(),
        "closed_at": "",
        "cwd": cwd,
        "git_branch": _git_branch(cwd),
    }
    write_session(session_id, session_data)

    # 3. RAG 컨텍스트가 주어지면 별도 마크다운 파일로 저장
    context_instruction = ""
    if rag_context:
        context_file_path = os.path.join(INBOX_DIR, f"{session_id}_context.md")
        with open(context_file_path, "w", encoding="utf-8") as f:
            f.write(rag_context)
        context_instruction = (
            f"🚨[필수] 작업을 시작하기 전에 {context_file_path} 파일을 열어 "
            f"팀 규칙 및 제공된 지식을 먼저 완벽히 숙지하십시오.🚨\n\n"
        )

    # 4. 전체 지시문은 '파일'로 저장한다.
    #    이유: iTerm 'write text'는 개행을 Enter로 전송하므로, 여러 줄 프롬프트를 직접 타이핑하면
    #          줄마다 따로 제출되어 프롬프트가 조각조각 깨진다. 그래서 자식에게는
    #          "이 파일을 읽고 따르라"는 '한 줄'만 보낸다(개행/이스케이프 문제 동시 해결).
    child_prompt = (
        f"[SYSTEM: SUB-AGENT ORCHESTRATION PROTOCOL]\n"
        f"당신은 고유 ID [{session_id}]를 부여받은 서브 에이전트(SAM)입니다.\n"
        f"현재 디렉토리에 CLAUDE.md 파일이 존재하더라도, 본 지시문의 규칙이 절대적으로 최우선합니다.\n\n"
        f"{context_instruction}"
        f"▶ 위임된 임무:\n{task}\n\n"
        f"⚠️ 필수 준수 규칙:\n"
        f"1. 임무를 완료하면 '반드시' 'report_result' 도구로 결과를 보고하십시오 (session_id='{session_id}').\n"
        f"2. 보고 완료 후에도 세션을 종료하지 말고, 부모 세션의 추가 지시(릴레이)를 대기하십시오."
    )
    prompt_file = os.path.join(INBOX_DIR, f"{session_id}_prompt.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(child_prompt)

    # 자식에게 보낼 '단 한 줄' (개행 없음 -> write text 1회로 안전하게 제출)
    launch_line = (
        f"너의 작업 지시문이 {prompt_file} 에 있다. 그 파일을 먼저 읽고 지시대로 수행하라. "
        f"(너의 세션 ID: {session_id})"
    )
    safe_launch = _as_escape(launch_line)

    # 권한 플래그: 새 탭마다 사람이 승인하지 않아도 무인으로 돌도록 한다.
    #   --permission-mode  : 권한 처리 모드(acceptEdits/bypassPermissions 등)
    #   --allowedTools      : 프롬프트 없이 허용할 도구(셸 작은따옴표로 감싸 *,(),: 등이 글로빙/해석되지 않게)
    perm_flags = f" --permission-mode {PERMISSION_MODE}"
    if ALLOWED_TOOLS:
        quoted_tools = " ".join(f"'{_sh_single_quote(t)}'" for t in ALLOWED_TOOLS)
        perm_flags += f" --allowedTools {quoted_tools}"
    cd_cmd = f"cd '{_sh_single_quote(cwd)}' ; {ENV_PREFIX}claude{perm_flags}"
    safe_cd_cmd = _as_escape(cd_cmd)

    applescript = f'''
    tell application "iTerm"
        if (count of windows) = 0 then
            set newWindow to (create window with default profile)
            set targetSession to current session of newWindow
        else
            tell current window
                set originalTab to current tab
                set newTab to (create tab with default profile)
                set targetSession to current session of newTab
                select originalTab
            end tell
        end if
        tell targetSession
            set myItermId to id
            write text "{safe_cd_cmd}"
            delay {BOOT_DELAY}
            write text "{safe_launch}"
            delay {PROMPT_DELAY}
            write text ""
        end tell
        return myItermId
    end tell
    '''
    result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
    if result.returncode != 0:
        # 탭 생성 실패: 흔적을 SPAWN_FAILED로 남겨 폴링이 헷갈리지 않게 한다.
        session_data["status"] = "SPAWN_FAILED"
        write_session(session_id, session_data)
        return f"[시스템 에러] iTerm2 탭 생성 실패: {result.stderr.strip()}"

    session_data["iterm_id"] = result.stdout.strip()
    write_session(session_id, session_data)

    return f"[시스템] 자식 세션 생성 성공! (ID: {session_id}, cwd: {cwd}) 백그라운드 작업 개시."
