import time
import os
import sys
from pathlib import Path
from typing import Any, Sequence

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from domain.langgraph.document_state import DocumentState


class FakeLLM:
    """LLM 대체: invoke 시 지정된 sleep을 수행하여 병렬 효과를 관찰."""
    def __init__(self, delay: float = 0.5, tag: str = "fake"):
        self.delay = delay
        self.tag = tag
        # model_name 호환 필드
        self.model_name = tag

    def invoke(self, messages: Sequence[BaseMessage]) -> Any:
        time.sleep(self.delay)
        # 간단한 응답
        text = "OK"
        # 섹션 타깃 추출용 마커 포함
        for m in messages:
            if isinstance(m, SystemMessage):
                text += "\nSECTION_TARGETS: overview,modules,changelog"
        class Resp:
            content = text
        return Resp()


def _run_change_analyzer_parallel_test():
    print("[TEST] change_analyzer_node: FILE_SUMMARY_MAX_CONCURRENCY effect")
    diff = """diff --git a/app/router.py b/app/router.py\n+ added line\n- removed line\ndiff --git a/app/service.py b/app/service.py\n+ added line\ndiff --git a/app/model.py b/app/model.py\n+ added line\ndiff --git a/app/util.py b/app/util.py\n+ added line\ndiff --git a/app/test_spec.py b/app/test_spec.py\n+ added line\n"""
    files = [
        "app/router.py",
        "app/service.py",
        "app/model.py",
        "app/util.py",
        "app/test_spec.py",
    ]
    state = DocumentState({
        "diff_content": diff,
        "changed_files": files,
        "code_change": {"commit_message": "Add features"}
    })

    # sequential
    os.environ["FILE_SUMMARY_MAX_CONCURRENCY"] = "1"
    t0 = time.time()
    s1 = change_analyzer_node(state.copy(), llm=FakeLLM(delay=0.5), use_mock=False)
    dur_seq = time.time() - t0

    # parallel
    os.environ["FILE_SUMMARY_MAX_CONCURRENCY"] = "4"
    t1 = time.time()
    s2 = change_analyzer_node(state.copy(), llm=FakeLLM(delay=0.5), use_mock=False)
    dur_par = time.time() - t1

    print(f"Sequential: {dur_seq:.2f}s, Parallel: {dur_par:.2f}s")
    assert dur_par < dur_seq * 0.7, "병렬 처리로 시간 단축이 충분하지 않습니다"


def _run_document_generator_parallel_test():
    print("[TEST] document_generator_node: PARTIAL_UPDATE_MAX_CONCURRENCY effect")
    existing_md = """# Title\n\n## Overview\nOld overview paragraph.\n\n## Architecture\nOld architecture paragraph.\n\n## Modules\nOld modules paragraph.\n\n## Changelog\n- old entry\n"""
    state = DocumentState({
        "should_update": True,
        "existing_document": {"content": existing_md, "title": "Title"},
        "analysis_result": "analysis",
        "changed_files": ["app/router.py", "app/service.py"],
        "file_change_summaries": [
            {"file": "app/router.py", "summary": "route updated", "priority": "high"},
            {"file": "app/service.py", "summary": "service updated", "priority": "high"},
        ],
        "code_change": {"commit_message": "Add features"},
        "target_doc_sections": ["overview", "architecture", "modules", "changelog"],
    })

    # sequential
    os.environ["PARTIAL_UPDATE_MAX_CONCURRENCY"] = "1"
    t0 = time.time()
    s1 = document_generator_node(state.copy(), llm=FakeLLM(delay=0.5), use_mock=False)
    dur_seq = time.time() - t0

    # parallel
    os.environ["PARTIAL_UPDATE_MAX_CONCURRENCY"] = "4"
    t1 = time.time()
    s2 = document_generator_node(state.copy(), llm=FakeLLM(delay=0.5), use_mock=False)
    dur_par = time.time() - t1

    print(f"Sequential: {dur_seq:.2f}s, Parallel: {dur_par:.2f}s")
    assert dur_par < dur_seq * 0.7, "병렬 처리로 시간 단축이 충분하지 않습니다"


if __name__ == "__main__":
    _run_change_analyzer_parallel_test()
    _run_document_generator_parallel_test()
    print("All parallel tests passed.")
