#!/usr/bin/env bash

# =====================================================================
# 🛸 SAM (Sub-Agent-MCP) 인프라 구축 및 자동화 셋팅 스크립트
# =====================================================================
# 사용법: 
# 1. 터미널에서 이 스크립트가 있는 폴더로 이동합니다.
# 2. chmod +x setup_sam.sh 명령어로 실행 권한을 부여합니다.
# 3. ./setup_sam.sh 명령어로 스크립트를 실행합니다.
# =====================================================================

set -e # 에러 발생 시 스크립트 즉시 중단

echo "📂 [1/3] 작업 디렉토리 확인 (이 스크립트가 있는 폴더를 SAM 루트로 사용)..."
# 저장소를 어디에 클론하든 동작하도록, 스크립트 자신의 위치를 루트로 잡는다.
TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TARGET_DIR"
echo "✅ SAM 루트: $TARGET_DIR"

echo "🐍 [2/3] 파이썬 가상환경(venv) 생성 및 필수 패키지 설치 중..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install mcp
echo "✅ 가상환경 및 패키지 설치 완료!"

echo "🤖 [3/3] Claude MCP 서버 전역(Global) 등록 중..."
if [ -f "sam_server.py" ]; then
    claude mcp add --scope user sub-agents-mcp -- "$TARGET_DIR/venv/bin/python" "$TARGET_DIR/sam_server.py"
    echo "✅ 신규 MCP 서버(sub-agents-mcp) 전역 등록 완료!"
else
    echo "⚠️  [안내] 디렉토리는 생성되었으나 sam_server.py 파일이 아직 없습니다."
    echo "    코드가 준비되면 다시 실행하거나 수동으로 등록해 주세요."
    exit 0
fi

echo ""
echo "🎉 모든 SAM 오케스트레이션 인프라 셋팅이 완료되었습니다🔥"
echo "💡 보안 가이드: 이제 새 프로젝트 폴더에서 'claude'를 처음 실행할 때,"
echo "   도구 권한 팝업이 뜨면 신중하게 검수하신 후 2번(영구 허용)을 선택해 주세요."
