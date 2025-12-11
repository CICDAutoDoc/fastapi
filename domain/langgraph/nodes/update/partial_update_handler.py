"""
부분 업데이트 핸들러

섹션 단위 부분 업데이트의 전체 워크플로우를 관리합니다.
"""

import os
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import ChatOpenAI
from ...document_state import DocumentState
from .section_parser import parse_markdown_sections, merge_sections
from .section_updater import update_section_llm, update_section_mock, infer_target_sections


def handle_partial_update(
    state: DocumentState,
    llm: Optional[ChatOpenAI],
    use_mock: bool
) -> DocumentState:
    """섹션 단위 부분 업데이트 처리"""
    existing = state.get('existing_document') or {}
    content = existing.get('content', '')
    if not content:
        state['error'] = 'No existing document content for partial update'
        state['status'] = 'error'
        return state
    
    parsed = parse_markdown_sections(content)
    
    file_summaries = state.get('file_change_summaries', [])
    analysis = state.get('analysis_result', '')
    changed_files = state.get('changed_files', []) or []
    commit_msg = (state.get('code_change') or {}).get('commit_message', '')
    target_sections = state.get('target_doc_sections') or infer_target_sections(changed_files)
    
    # architecture가 선택되면 overview와 diagram도 자동 포함
    if 'architecture' in target_sections:
        if 'overview' not in target_sections:
            target_sections.append('overview')
        if 'diagram' not in target_sections:
            target_sections.append('diagram')
    
    max_chars = int(os.getenv('PARTIAL_DOC_UPDATE_MAX_SECTION_CHARS', '6000'))
    
    updates = []
    updated_map: Dict[str, str] = {}
    
    # LLM 초기화
    if not use_mock and llm is None:
        api_key = os.getenv('OPENAI_API_KEY') or ''
        if not api_key:
            use_mock = True
            print('[DocumentGenerator/Partial] No API key, using mock mode')
        else:
            llm = ChatOpenAI(model='gpt-5', temperature=0.2)
            print('[DocumentGenerator/Partial] LLM initialized')
    
    # 병렬 처리 활성화 여부 (섹션 수 >1 && 환경변수)
    max_workers = int(os.getenv('PARTIAL_UPDATE_MAX_CONCURRENCY', '5'))
    max_workers = max(1, max_workers)

    def _process_section(section_key: str) -> tuple[str, str, int, int, bool]:
        import time
        import threading
        thread_id = threading.current_thread().name
        start = time.time()
        print(f"  [{thread_id}] 시작: 섹션 '{section_key}' 업데이트")
        
        sec_old = parsed.sections.get(section_key, '')
        if not sec_old and section_key != 'changelog':
            sec_old = ''
        trimmed_old = sec_old[:max_chars] if len(sec_old) > max_chars else sec_old
        if use_mock:
            new_text_local = update_section_mock(section_key, trimmed_old, commit_msg)
        else:
            # 스레드 안전을 위해 새 LLM 인스턴스를 생성 (모델명 동일)
            llm_model = getattr(llm, 'model_name', getattr(llm, 'model', 'gpt-5')) if llm else 'gpt-5'
            local_llm = llm if max_workers == 1 else ChatOpenAI(model=llm_model, temperature=0.2)
            # 타입 안전성 확보
            if local_llm is None:
                new_text_local = sec_old
            else:
                new_text_local = update_section_llm(section_key, trimmed_old, local_llm, file_summaries, analysis or '', commit_msg)
        changed_flag = new_text_local.strip() != sec_old.strip()
        
        elapsed = time.time() - start
        print(f"  [{thread_id}] 완료: 섹션 '{section_key}' ({elapsed:.2f}s, 변경={changed_flag})")
        return section_key, new_text_local, len(sec_old), len(new_text_local), changed_flag

    if len(target_sections) > 1 and max_workers > 1 and not use_mock:
        import time
        workers = min(max_workers, len(target_sections))
        print(f"[섹션 업데이트 병렬 처리] {len(target_sections)}개 섹션, {workers}개 워커 사용")
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_process_section, k): k for k in target_sections}
            for fut in as_completed(futures):
                k, new_text, old_len, new_len, changed_flag = fut.result()
                updated_map[k] = new_text
                updates.append({'key': k, 'old_length': old_len, 'new_length': new_len, 'changed': changed_flag})
        elapsed = time.time() - start_time
        print(f"[섹션 업데이트 병렬 완료] {elapsed:.2f}초 소요")
    else:
        # 순차 처리
        import time
        print(f"[섹션 업데이트 순차 처리] {len(target_sections)}개 섹션")
        start_time = time.time()
        for k in target_sections:
            k2, new_text, old_len, new_len, changed_flag = _process_section(k)
            updated_map[k2] = new_text
            updates.append({'key': k2, 'old_length': old_len, 'new_length': new_len, 'changed': changed_flag})
        elapsed = time.time() - start_time
        print(f"[섹션 업데이트 순차 완료] {elapsed:.2f}초 소요")
    
    # 섹션 병합
    merged_body = merge_sections(parsed, updated_map)
    title = existing.get('title') or state.get('document_title') or 'Project Documentation'
    new_content = f"# {title}\n\n{merged_body}"
    
    state['document_content'] = new_content
    state['updated_sections'] = updates
    state['document_summary'] = f"Incremental update applied to sections: {', '.join(target_sections)}"
    state['status'] = 'saving'
    
    print(f"[DocumentGenerator/Partial] Updated {len(updates)} sections: {', '.join(target_sections)}")
    return state
