"""
섹션 업데이트 프롬프트 빌더

LLM용 섹션 업데이트 프롬프트를 생성합니다.
"""

from typing import List, Tuple


def build_section_prompt(
    section_key: str,
    old_text: str,
    file_summaries: List[dict],
    analysis: str,
    commit_msg: str
) -> Tuple[str, str]:
    """
    문서 섹션 업데이트용 system/user 프롬프트 생성.
    - changelog는 특별 처리 (항상 새 항목만 생성)
    - 그 외 섹션은 전체 재생성
    """

    # ------------------------------------------------------------
    # 1) Overview — 완전 재생성
    # ------------------------------------------------------------
    if section_key == "overview":
        system_prompt = (
            "당신의 역할은 프로젝트 개요 문서 전문가입니다.\n"
            "기존 개요를 참고하여 변경사항을 반영한 새로운 프로젝트 개요를 완전히 재생성하세요.\n\n"
            "템플릿 고정 (반드시 준수):\n"
            "## 1. 목적\n"
            "## 2. 주요 기능\n"
            "## 3. 기술 스택\n"
            "## 4. 아키텍처 개요\n"
            "## 5. 강점/특징\n\n"
            "규칙:\n"
            "- 기존 개요의 구조를 기반으로 하되, 변경사항을 반영하여 내용 업데이트\n"
            "- 위 5개 서브섹션 구조를 절대 변경하지 말 것\n"
            "- 마커([UPDATE], [ADD] 등) 사용 금지, 순수 Markdown 내용만 출력\n"
            "- Mermaid 다이어그램 생성 금지\n"
            "- 부가 설명이나 주석 금지\n"
        )

        summaries_text = "\n".join([
            f"- {s.get('file')} ({s.get('priority')}): {s.get('summary')}"
            for s in file_summaries
        ])

        user_prompt = (
            f"기존 개요:\n{old_text}\n\n"
            f"커밋 메시지:\n{commit_msg}\n\n"
            f"변경된 파일 요약:\n{summaries_text}\n\n"
            f"변경 분석:\n{analysis}\n\n"
            "위 정보를 기반으로 기존 개요를 참고하여 변경사항을 반영한 새로운 프로젝트 개요를 완전히 재생성하세요.\n"
            "출력: 5개 서브섹션 구조를 유지하면서 내용만 업데이트하세요. 다른 텍스트는 절대 포함하지 마세요."
        )

        return system_prompt, user_prompt

    # ------------------------------------------------------------
    # 2) Architecture — 완전 재생성
    # ------------------------------------------------------------
    if section_key == "architecture":
        system_prompt = (
            "당신의 역할은 시스템 아키텍처 문서 전문가입니다.\n"
            "기존 아키텍처 설명을 참고하여 변경사항을 반영한 새로운 아키텍처 문서를 완전히 재생성하세요.\n\n"
            "템플릿 고정 (반드시 준수):\n"
            "## 1. 계층 구조\n"
            "## 2. 주요 컴포넌트\n"
            "## 3. 데이터/제어 흐름\n"
            "## 4. 설계 고려사항\n\n"
            "규칙:\n"
            "- 기존 아키텍처의 구조를 기반으로 하되, 변경사항을 반영하여 내용 업데이트\n"
            "- 위 4개 서브섹션 구조를 절대 변경하지 말 것\n"
            "- 마커([UPDATE], [ADD] 등) 사용 금지, 순수 Markdown 내용만 출력\n"
            "- Mermaid 다이어그램 생성 금지\n"
            "- 부가 설명이나 주석 금지\n"
        )

        summaries_text = "\n".join([
            f"- {s.get('file')} ({s.get('priority')}): {s.get('summary')}"
            for s in file_summaries
        ])

        user_prompt = (
            f"기존 아키텍처:\n{old_text}\n\n"
            f"커밋 메시지:\n{commit_msg}\n\n"
            f"변경된 파일 요약:\n{summaries_text}\n\n"
            f"변경 분석:\n{analysis}\n\n"
            "위 정보를 기반으로 기존 아키텍처를 참고하여 변경사항을 반영한 새로운 아키텍처 문서를 완전히 재생성하세요.\n"
            "출력: 4개 서브섹션 구조를 유지하면서 내용만 업데이트하세요. 다른 텍스트는 절대 포함하지 마세요."
        )

        return system_prompt, user_prompt

    # ------------------------------------------------------------
    # 3) Modules — 완전 재생성
    # ------------------------------------------------------------
    if section_key == "modules":
        system_prompt = (
            "당신의 역할은 핵심 모듈 문서 전문가입니다.\n"
            "기존 모듈 설명을 참고하여 변경사항을 반영한 새로운 모듈 문서를 완전히 재생성하세요.\n\n"
            "템플릿 고정 (반드시 준수):\n"
            "각 모듈은 다음 구조를 따릅니다:\n"
            "### [모듈명]\n"
            "- 목적: \n"
            "- 핵심 기능: (불릿 2~6개)\n"
            "- 의존성: (내부/외부 의존성)\n"
            "- 기술 특성: (사용 기술과 패턴)\n"
            "- 개선 포인트: (1~3개)\n\n"
            "규칙:\n"
            "- 기존 모듈 문서의 구조를 기반으로 하되, 변경사항을 반영하여 내용 업데이트\n"
            "- 각 모듈의 5가지 항목 구조를 절대 변경하지 말 것\n"
            "- 마커([UPDATE], [ADD] 등) 사용 금지, 순수 Markdown 내용만 출력\n"
            "- Mermaid 다이어그램 생성 금지\n"
            "- 부가 설명이나 주석 금지\n"
        )

        summaries_text = "\n".join([
            f"- {s.get('file')} ({s.get('priority')}): {s.get('summary')}"
            for s in file_summaries
        ])

        user_prompt = (
            f"기존 모듈 문서:\n{old_text}\n\n"
            f"커밋 메시지:\n{commit_msg}\n\n"
            f"변경된 파일 요약:\n{summaries_text}\n\n"
            f"변경 분석:\n{analysis}\n\n"
            "위 정보를 기반으로 기존 모듈 문서를 참고하여 변경사항을 반영한 새로운 모듈 문서를 완전히 재생성하세요.\n"
            "출력: 각 모듈의 5가지 항목 구조를 유지하면서 내용만 업데이트하세요. 다른 텍스트는 절대 포함하지 마세요."
        )

        return system_prompt, user_prompt

    # ------------------------------------------------------------
    # 4) Diagram — 완전 재생성
    # ------------------------------------------------------------
    if section_key == "diagram":
        system_prompt = (
            "당신의 역할은 시스템 아키텍처 다이어그램 전문가입니다.\n"
            "기존 다이어그램을 참고하여 변경사항을 반영한 새로운 Mermaid 다이어그램을 완전히 재생성하세요.\n\n"
            "규칙:\n"
            "- 기존 다이어그램 구조를 기반으로 하되, 변경사항을 반영하여 전체를 다시 생성\n"
            "- 반드시 ```mermaid\\n(내용)\\n``` 형식으로만 출력\n"
            "- ```mermaid를 다른 백틱이나 따옴표로 대체/이스케이프 금지\n"
            "- graph LR 또는 graph TD 한 개만 생성\n"
            "- 노드 <= 12개, 엣지 <= 20개\n"
            "- 자기 루프 금지\n"
            "- 실제 파일/폴더 구조 기반으로 노드 생성\n"
            "- 마커([UPDATE], [ADD] 등) 사용 금지, 순수 Mermaid 코드만 출력\n"
            "- 부가 설명이나 주석 금지\n"
        )

        summaries_text = "\n".join([
            f"- {s.get('file')} ({s.get('priority')}): {s.get('summary')}"
            for s in file_summaries
        ])

        user_prompt = (
            f"기존 다이어그램:\n{old_text}\n\n"
            f"커밋 메시지:\n{commit_msg}\n\n"
            f"변경된 파일 요약:\n{summaries_text}\n\n"
            f"변경 분석:\n{analysis}\n\n"
            "위 정보를 기반으로 기존 다이어그램을 참고하여 변경사항을 반영한 새로운 Mermaid 다이어그램을 완전히 재생성하세요.\n"
            "출력: ```mermaid로 시작하는 코드블록만 출력하세요. 다른 텍스트는 절대 포함하지 마세요."
        )

        return system_prompt, user_prompt

    # ------------------------------------------------------------
    # 5) Changelog — 특별 처리
    # ------------------------------------------------------------
    if section_key == "changelog":

        system_prompt = (
            "당신의 역할은 changelog 작성자입니다.\n"
            "이번 커밋에서 새로 발생한 변화만을 요약하여 '신규 changelog 항목'만 생성하세요.\n\n"
            "규칙:\n"
            "- 기존 changelog 내용은 다시 언급하지 않습니다.\n"
            "- 출력 형식: 새로운 bullet 한 개 또는 1~3줄의 짧은 항목\n"
            "- 불필요한 설명, 헤더, Markdown 코드블록 금지\n"
            "- 커밋과 직접 관련된 변경 사항만 포함\n"
        )

        summaries_text = "\n".join([
            f"- {s.get('file')}: {s.get('summary')}"
            for s in file_summaries[:5]  # 상위 5개만
        ])

        user_prompt = (
            f"커밋 메시지:\n{commit_msg}\n\n"
            f"변경된 파일 요약(일부):\n{summaries_text}\n\n"
            f"변경 분석:\n{analysis}\n\n"
            "위 정보를 기반으로 이번 커밋의 새로운 changelog 항목을 생성하세요.\n"
            "출력: 하나의 새로운 bullet만 생성하세요."
        )

        return system_prompt, user_prompt

    # 여기에 도달하면 안 되는 섹션
    raise ValueError(f"Unknown section_key: {section_key}")
