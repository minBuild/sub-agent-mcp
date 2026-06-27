import os

# SAM 루트 디렉토리.
# 우선순위: 환경변수 SAM_HOME > 이 파일(sam_config.py)이 있는 디렉토리.
# 덕분에 저장소를 어디에 클론하든 그대로 동작한다(고정 경로 가정 없음).
BASE_DIR = os.path.expanduser(os.environ.get("SAM_HOME", "")) or os.path.dirname(os.path.abspath(__file__))

# 전역 인박스 경로
INBOX_DIR = os.path.join(BASE_DIR, ".sam_inbox")
os.makedirs(INBOX_DIR, exist_ok=True)

# 부모 세션의 현재 작업 디렉토리 (MCP 서버 프로세스 기동 시점의 cwd).
# ⚠️ 이건 '부모 Claude가 보던 repo'가 아니라 'MCP 서버가 뜬 디렉토리'다.
#    자식을 다른 디렉토리에서 띄우려면 delegate_to_sam(working_dir=...) 인자를 쓴다.
CURRENT_DIR = os.getcwd()

# 쉘 환경 변수 로드 접두어.
# 새 iTerm 탭은 이미 로그인 셸로 .zshrc를 읽지만, 안전을 위해 한 번 더 source한다.
# 2>/dev/null 로 .zshrc의 비치명적 에러가 명령 전체를 죽이지 않게 한다.
ENV_PREFIX = "source ~/.zshrc 2>/dev/null ; "

# --- 타이밍 (터미널 자동화라 본질적으로 타이밍에 민감하다) ---
# claude CLI가 떠서 프롬프트 입력을 받을 준비가 될 때까지 대기(초). 머신이 느리면 늘려라.
BOOT_DELAY = 6
# 지시문을 타이핑한 뒤 Enter(빈 줄)를 보내기까지의 대기(초).
PROMPT_DELAY = 0.5

# RUNNING 상태가 이 분(min)을 넘기면 check_inbox에서 '죽었을 수 있음' 경고를 띄운다.
STALE_MINUTES = 30

# --- 자식 세션 권한 (무인 병렬 실행의 핵심) ---
# 문제: 자식 claude가 새 탭마다 권한 프롬프트를 띄우면, 사람이 탭마다 들어가
#       승인해줄 때까지 RUNNING 상태로 '멈춤(hang)'한다 -> 동시 위임의 의미가 사라진다.
#
# 해결: ① ALLOWED_TOOLS 로 자식이 쓰는 도구를 미리 허용 -> 프롬프트 자체가 안 뜸(매끄러운 정상 경로).
#       ② PERMISSION_MODE 로 권한 처리 모드를 지정.
#
# PERMISSION_MODE: default | acceptEdits | plan | bypassPermissions
#   - acceptEdits      : 파일 편집은 자동승인. 그 외(Bash/WebFetch 등)는 ALLOWED_TOOLS로 허용.
#   - bypassPermissions: 모든 프롬프트 스킵. 가장 강력하지만 신뢰된 작업에만 사용.
# 환경변수 SAM_PERMISSION_MODE 로 덮어쓸 수 있다.
PERMISSION_MODE = os.environ.get("SAM_PERMISSION_MODE", "acceptEdits")

# 프롬프트 없이 허용할 도구 목록. 여기 없는 도구를 자식이 쓰려 하면
# (acceptEdits 모드 기준) 여전히 프롬프트가 떠 멈출 수 있으니, 자식이 쓰는 도구는 빠짐없이 넣는다.
# claude CLI 의 --allowedTools 로 그대로 전달된다.
ALLOWED_TOOLS = [
    "WebFetch",
    "WebSearch",
    "Bash(curl:*)",
]
