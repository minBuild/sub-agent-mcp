from mcp.server.fastmcp import FastMCP

from tools.delegate import delegate_to_sam
from tools.report import report_result
from tools.inbox import check_inbox
from tools.message import send_message
from tools.close import close_session

# 1. MCP 서버 초기화
mcp = FastMCP("SAM (Sub-Agent-MCP) OS")

# 2. 명시적으로 도구 등록
mcp.tool(name="delegate_to_sam", description="독립된 AI 자식 세션(SAM)을 생성하고 작업을 위임")(delegate_to_sam)
mcp.tool(name="report_result", description="자식 에이전트가 작업 완료 후 결과를 구조화해서 보고")(report_result)
mcp.tool(name="check_inbox", description="생성된 자식 세션들의 완료 여부를 폴링하여 결과를 수집")(check_inbox)
mcp.tool(name="send_message", description="대기 중인 자식 세션에게 추가 지시를 전달")(send_message)
mcp.tool(name="close_session", description="작업이 끝난 세션의 인박스 파일을 삭제하고 iTerm2 탭을 종료")(close_session)

if __name__ == "__main__":
    mcp.run(transport='stdio')
