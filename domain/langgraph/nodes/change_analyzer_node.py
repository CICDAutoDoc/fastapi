"""
② 변경사항 분석 노드

LLM 또는 Mock을 사용하여 코드 변경사항을 분석하는 노드
"""
from typing import Optional
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..utils.llm_backoff import invoke_with_retry

from ..document_state import DocumentState


def change_analyzer_node(
    state: DocumentState,
    llm: Optional[ChatOpenAI] = None,
    use_mock: bool = False
) -> DocumentState:
    """
    변경사항 분석 노드
    
    역할:
        - Git diff를 분석하여 변경사항 요약 생성
        - Mock 모드: 템플릿 기반 분석
        - 실제 모드: LLM 기반 상세 분석
    
    입력:
        - diff_content: Git diff 내용
        - changed_files: 변경된 파일 목록
        - code_change: 커밋 정보
        - llm: ChatOpenAI 인스턴스 (실제 모드)
        - use_mock: Mock 모드 사용 여부
    
    출력:
        - analysis_result: 변경사항 분석 결과
        - status: "generating"
    """
    try:
        diff_content = state.get("diff_content", "")
        changed_files = state.get("changed_files", []) or []
        code_change = state.get("code_change") or {}
        commit_message = code_change.get("commit_message", "") if isinstance(code_change, dict) else ""
        
        # 파일별 변경사항 요약 생성
        file_change_summaries = _generate_file_summaries(changed_files, diff_content, use_mock, llm)
        state["file_change_summaries"] = file_change_summaries
        
        if use_mock:
            # Mock 응답 + 타겟 섹션 추론
            line_adds = diff_content.count('+') if diff_content else 0
            analysis = (
                "## 주요 변경사항\n"
                f"- 파일 수정: {', '.join(changed_files)}\n"
                f"- 커밋 메시지: {commit_message}\n\n"
                "## 변경 이유\n코드 개선 및 기능 추가를 위한 변경\n\n"
                "## 영향 범위\n수정된 파일들의 관련 기능에 영향\n\n"
                "## 기술적 세부사항\n"
                f"- 추가/수정 라인(+): {line_adds}\n"
            )
            state["analysis_result"] = analysis
            state["target_doc_sections"] = _identify_target_sections(changed_files)
            state["status"] = "generating"
            return state
        
        # 실제 LLM 분석
        if llm is None:
            raise ValueError("LLM is required for non-mock mode")
        
        system_prompt = (
            "당신은 코드 변경사항을 분석하여 '문서 업데이트가 필요한 섹션'을 식별하는 전문가입니다.\n"
            "다음 정보를 생성하세요:\n"
            "1. 주요 변경사항 (불릿)\n"
            "2. 변경 이유 (간단)\n"
            "3. 영향 범위 (모듈/레이어 관점)\n"
            "4. 기술적 세부사항 (라이브러리/패턴)\n"
            "5. 문서 섹션 추천: overview | architecture | modules | changelog 중 해당되는 것들만 콤마로 나열\n"
            "출력은 Markdown, 마지막 줄에 'SECTION_TARGETS:' 뒤에 섹션 키들을 소문자로 콤마구분으로 작성. 예: SECTION_TARGETS: overview,modules,changelog\n"
            "불필요한 추측은 피하고 diff 기반으로 판단.\n"
        )

        user_prompt = f"""커밋 메시지: {commit_message}

변경된 파일들:
{', '.join(changed_files)}

Git Diff:
{diff_content}

위 코드 변경사항을 분석하여 요약해주세요."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # 레이트리밋 대비 재시도 래퍼 사용
        response = invoke_with_retry(llm, messages)
        
        analysis_text = str(response.content) if hasattr(response, 'content') else str(response)
        state["analysis_result"] = analysis_text
        state["target_doc_sections"] = _extract_section_targets(analysis_text)
        state["status"] = "generating"
        return state
        
    except Exception as e:
        state["error"] = f"Change analyzer failed: {str(e)}"
        state["status"] = "error"
        return state


def _extract_section_targets(text: str) -> list[str]:
    import re
    m = re.search(r'SECTION_TARGETS:\s*([a-z,]+)', text.lower())
    if not m:
        return []
    raw = m.group(1)
    return [x.strip() for x in raw.split(',') if x.strip()]


def _identify_target_sections(changed_files: list[str]) -> list[str]:
    targets = set()
    for f in changed_files:
        lf = f.lower()
        if any(x in lf for x in ['main','app','config']):
            targets.add('overview')
        if any(x in lf for x in ['router','endpoint','controller']):
            targets.add('architecture'); targets.add('modules')
        if any(x in lf for x in ['model','schema','entity']):
            targets.add('modules')
        if any(x in lf for x in ['service','handler']):
            targets.add('modules')
    targets.add('changelog')  # 항상 변경 이력 추가
    return list(targets)


from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Optional, List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


def _detect_change_type(file_diff: str) -> str:
    """파일별 diff 기반으로 정확하게 변경 타입 판별"""
    if not file_diff:
        return "modified"
    if "+++ /dev/null" in file_diff:
        return "deleted"
    if "--- /dev/null" in file_diff:
        return "added"
    return "modified"


def _build_prompt(file: str, file_diff: str) -> str:
    """프롬프트 품질 개선"""
    # 변경된 라인만 추출
    changed = []
    for line in file_diff.split("\n"):
        if line.startswith("+") or line.startswith("-"):
            changed.append(line)
        if len(changed) > 120:   # LLM 인풋 과다 방지
            break

    diff_excerpt = "\n".join(changed[:120])

    return (
        f"다음 파일의 변경사항을 1-2문장으로 요약하세요.\n"
        f"파일: {file}\n\n"
        f"변경된 핵심 라인:\n{diff_excerpt[:1500]}\n\n"
        f"요약:"
    )


def _generate_file_summaries(
    changed_files: list[str],
    diff_content: str,
    use_mock: bool,
    llm: Optional[ChatOpenAI]
) -> list[dict]:
    """파일별 변경사항 요약 생성 (개선 버전)"""

    summaries: list[dict] = []

    # ============================
    # 1) Mock 모드 처리
    # ============================
    if use_mock:
        for file in changed_files:
            file_diff = _extract_file_diff(file, diff_content)
            change_type = _detect_change_type(file_diff)
            summaries.append({
                "file": file,
                "change_type": change_type,
                "summary": f"{file} 파일이 {change_type}되었습니다.",
                "priority": _get_file_priority(file)
            })
        return summaries

    # ============================
    # 2) LLM 객체 없음 → fallback
    # ============================
    if llm is None:
        for f in changed_files:
            file_diff = _extract_file_diff(f, diff_content)
            summaries.append({
                "file": f,
                "change_type": _detect_change_type(file_diff),
                "summary": f"{f} 파일 변경",
                "priority": _get_file_priority(f)
            })
        return summaries

    # ============================
    # 3) 우선순위 분리
    # ============================
    high_medium = []
    for f in changed_files:
        p = _get_file_priority(f)
        if p == "low":
            file_diff = _extract_file_diff(f, diff_content)
            change_type = _detect_change_type(file_diff)
            summaries.append({
                "file": f,
                "change_type": change_type,
                "summary": f"{f} ({change_type})",
                "priority": p
            })
        else:
            high_medium.append((f, p))

    max_workers = int(os.getenv("FILE_SUMMARY_MAX_CONCURRENCY", "4"))
    max_workers = max(1, max_workers)

    # ============================
    # 4) 병렬 LLM 처리 함수
    # ============================
    def _summarize(file: str, priority: str) -> dict:
        import time
        import threading
        thread_id = threading.current_thread().name
        start = time.time()
        print(f"  [{thread_id}] 시작: {file} (우선순위: {priority})")
        
        file_diff = _extract_file_diff(file, diff_content)
        change_type = _detect_change_type(file_diff)

        if not file_diff:
            result = {
                "file": file,
                "change_type": change_type,
                "summary": f"{file} 파일 {change_type}",
                "priority": priority
            }
            print(f"  [{thread_id}] 완료: {file} ({time.time()-start:.2f}s) - diff 없음")
            return result

        prompt = _build_prompt(file, file_diff)

        try:
            resp = invoke_with_retry(llm, [HumanMessage(content=prompt)])
            text = str(getattr(resp, "content", resp))
        except Exception as e:
            print(f"  [{thread_id}] 오류: {file} - {str(e)[:50]}")
            text = f"{file} 파일 {change_type}"

        result = {
            "file": file,
            "change_type": change_type,
            "summary": text,
            "priority": priority
        }
        print(f"  [{thread_id}] 완료: {file} ({time.time()-start:.2f}s)")
        return result

    # ============================
    # 5) 병렬 실행
    # ============================
    if high_medium:
        import time
        workers = min(max_workers, len(high_medium))
        if workers > 1:
            print(f"[파일 요약 병렬 처리] {len(high_medium)}개 파일, {workers}개 워커 사용")
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(_summarize, f, p): (f, p) for f, p in high_medium}
                for fut in as_completed(futures):
                    summaries.append(fut.result())
            elapsed = time.time() - start_time
            print(f"[파일 요약 병렬 완료] {elapsed:.2f}초 소요")
        else:
            print(f"[파일 요약 순차 처리] {len(high_medium)}개 파일")
            start_time = time.time()
            for f, p in high_medium:
                summaries.append(_summarize(f, p))
            elapsed = time.time() - start_time
            print(f"[파일 요약 순차 완료] {elapsed:.2f}초 소요")

    # ============================
    # 6) 입력 순서 유지
    # ============================
    order_map = {s["file"]: s for s in summaries}
    return [order_map[f] for f in changed_files if f in order_map]



def _get_file_priority(filepath: str) -> str:
    """파일 우선순위 판단 (high/medium/low)"""
    lower = filepath.lower()
    
    # High priority: 라우터, 스키마, 서비스, 보안, DB 설정
    if any(x in lower for x in ['router', 'endpoint', 'controller', 'api']):
        return "high"
    if any(x in lower for x in ['schema', 'model', 'entity']):
        return "high"
    if any(x in lower for x in ['service', 'handler', 'manager']):
        return "high"
    if any(x in lower for x in ['auth', 'security', 'permission']):
        return "high"
    if any(x in lower for x in ['database', 'migration', 'config']):
        return "high"
    
    # Medium priority: 유틸, 미들웨어, 테스트
    if any(x in lower for x in ['util', 'helper', 'middleware']):
        return "medium"
    if any(x in lower for x in ['test', 'spec']):
        return "medium"
    
    # Low priority: 기타
    return "low"


def _extract_file_diff(filename: str, full_diff: str) -> str:
    """전체 diff에서 특정 파일의 diff만 추출"""
    import re
    # diff --git a/filename 패턴으로 파일 구분
    pattern = rf"diff --git a/{re.escape(filename)}.*?(?=diff --git|$)"
    match = re.search(pattern, full_diff, re.DOTALL)
    if match:
        return match.group(0)
    return ""
