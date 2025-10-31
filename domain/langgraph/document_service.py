"""
문서 처리 서비스
데이터베이스와 연동하여 문서를 생성, 업데이트, 조회하는 서비스
"""
from typing import Dict, List, Optional, Any, cast
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import CodeChange, FileChange, Document
from .document_generator import DocumentGenerator, CodeChangeInput, get_document_generator
from app.logging_config import get_logger

logger = get_logger("document_service")


class DocumentService:
    """문서 처리 서비스"""

    def __init__(self, use_mock: bool = False):
        if use_mock:
            from .document_generator import MockDocumentGenerator
            self.generator = MockDocumentGenerator()
            logger.info("DocumentService initialized with MockDocumentGenerator")
        else:
            self.generator = get_document_generator()
            logger.info("DocumentService initialized with real DocumentGenerator")

    async def process_code_change(self, code_change_id: int) -> Dict[str, Any]:
        """
        코드 변경사항으로부터 문서를 생성하거나 업데이트

        Args:
            code_change_id: CodeChange 테이블의 ID

        Returns:
            처리 결과
        """
        session = SessionLocal()
        try:
            logger.info(f"Processing code change: {code_change_id}")

            # 코드 변경사항 가져오기
            code_change = session.query(CodeChange).filter(
                CodeChange.id == code_change_id
            ).first()

            if not code_change:
                logger.error(f"CodeChange not found: {code_change_id}")
                return {
                    "success": False,
                    "error": f"CodeChange not found: {code_change_id}"
                }

            # 저장소별 기존 문서 확인 (커밋별이 아닌 저장소별로)
            repository_name = code_change.repository.full_name if code_change.repository else "unknown"
            existing_doc = session.query(Document).filter(
                Document.repository_name == repository_name,
                Document.document_type == "repository"  # 저장소 전체 문서 타입
            ).first()

            if existing_doc:
                # 기존 저장소 문서에 새 커밋 내용 추가
                logger.info(
                    f"Adding commit {code_change.commit_sha} to existing repository document: {repository_name}")
                return await self._append_to_repository_document(session, existing_doc, code_change)
            else:
                # 저장소의 첫 번째 문서 생성
                logger.info(f"Creating first repository document for: {repository_name}")
                return await self._create_new_document(session, code_change)

        except Exception as e:
            logger.error(f"Error processing code change {code_change_id}: {str(e)}", exc_info=True)
            session.rollback()
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}"
            }
        finally:
            session.close()

    async def _create_new_document(self, session: Session, code_change: CodeChange) -> Dict[str, Any]:
        """저장소의 첫 번째 문서 생성 (새로운 구조)"""
        try:
            # 파일 변경사항 가져오기
            file_changes = session.query(FileChange).filter(
                FileChange.code_change_id == code_change.id
            ).all()

            logger.info(f"Found {len(file_changes)} file changes for code change {code_change.id}")

            # 생성기 입력 데이터 준비
            code_input = self._prepare_code_input(code_change, file_changes)

            repository_name = code_change.repository.full_name if code_change.repository else "unknown"

            # 저장소 전체 문서 상태를 pending으로 먼저 저장
            # commit_sha는 고유해야 하므로 repository 식별자를 추가
            unique_commit_sha = f"{repository_name}#{code_change.commit_sha}"

            document = Document(
                title=f"{repository_name} - 프로젝트 문서",
                content="# 프로젝트 문서 생성 중...\n\n이 문서는 저장소의 모든 변경사항을 추적합니다.",
                summary="",
                status="pending",
                document_type="repository",  # 저장소 전체 문서
                commit_sha=unique_commit_sha,  # 저장소별 고유 식별자
                repository_name=repository_name,
                generation_metadata={
                    "started_at": datetime.utcnow().isoformat(),
                    "commits": [str(code_change.commit_sha)],  # 실제 커밋 SHA 리스트
                    "commit_count": 1,
                    "latest_commit": str(code_change.commit_sha)  # 최신 커밋 추적
                },
                code_change_id=code_change.id
            )

            session.add(document)
            session.commit()
            session.refresh(document)

            logger.info(f"Created pending document with ID: {document.id}")

            # 문서 생성
            result = await self.generator.generate_document(code_input)

            if result["success"]:
                # 성공적으로 생성된 경우 업데이트
                cast(Any, document).title = f"{repository_name} - {result['title']}"  # type: ignore
                cast(Any, document).content = result["content"]  # type: ignore
                cast(Any, document).summary = result.get("summary", "")  # type: ignore
                cast(Any, document).status = "generated"  # type: ignore

                # 메타데이터에 저장소 정보 유지
                metadata = result.get("metadata", {})
                metadata.update({
                    "commits": [code_change.commit_sha],
                    "commit_count": 1,
                    "last_updated": datetime.utcnow().isoformat()
                })
                cast(Any, document).generation_metadata = metadata  # type: ignore
                cast(Any, document).updated_at = datetime.utcnow()  # type: ignore

                session.commit()

                logger.info(f"Successfully generated document {document.id}: {document.title}")

                return {
                    "success": True,
                    "action": "created",
                    "document_id": document.id,
                    "title": document.title,
                    "summary": document.summary
                }
            else:
                # 실패한 경우 상태 업데이트
                document.title = result.get("title", f"문서 생성 실패: {code_change.commit_message[:50]}")
                document.content = result.get("content", f"# 문서 생성 실패\n\n{result.get('error', 'Unknown error')}")
                document.summary = result.get("summary", f"문서 생성 실패: {result.get('error', 'Unknown error')}")
                cast(Any, document).status = "failed"  # type: ignore
                document.generation_metadata = result.get("metadata", {})
                cast(Any, document).updated_at = datetime.utcnow()  # type: ignore

                session.commit()

                logger.error(f"Failed to generate document {document.id}: {result.get('error', 'Unknown error')}")

                return {
                    "success": False,
                    "action": "created_failed",
                    "document_id": document.id,
                    "error": result.get("error", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error creating new document: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Document creation failed: {str(e)}"
            }

    async def _append_to_repository_document(self, session: Session, document: Document, code_change: CodeChange) -> \
    Dict[str, Any]:
        """기존 저장소 문서에 새 커밋 내용 추가"""
        try:
            # 파일 변경사항 가져오기
            file_changes = session.query(FileChange).filter(
                FileChange.code_change_id == code_change.id
            ).all()

            logger.info(f"Appending code change {code_change.id} to repository document {document.id}")

            # 메타데이터에서 기존 커밋 목록 가져오기
            metadata = document.generation_metadata or {}
            existing_commits = metadata.get("commits", [])

            # 중복 커밋 체크 (실제 커밋 SHA로)
            commit_sha_str = str(code_change.commit_sha)
            if commit_sha_str in existing_commits:
                logger.info(f"Commit {code_change.commit_sha} already exists in document {document.id}")
                return {
                    "success": True,
                    "action": "already_exists",
                    "document_id": document.id,
                    "message": "커밋이 이미 문서에 포함되어 있습니다."
                }

            # 상태를 updating으로 설정
            cast(Any, document).status = "updating"  # type: ignore
            cast(Any, document).updated_at = datetime.utcnow()  # type: ignore
            session.commit()

            # 새로운 변경사항을 포함한 입력 데이터 준비 (누적)
            code_input = self._prepare_cumulative_code_input(document, code_change, file_changes)

            # 문서 재생성 (기존 내용 + 새 내용)
            result = await self.generator.generate_document(code_input)

            if result["success"]:
                # 문서 업데이트
                cast(Any, document).title = f"{document.repository_name} - {result['title']}"  # type: ignore
                cast(Any, document).content = result["content"]  # type: ignore
                cast(Any, document).summary = result.get("summary", "")  # type: ignore
                cast(Any, document).status = "generated"  # type: ignore
                # commit_sha를 저장소별 고유 식별자로 업데이트
                unique_commit_sha = f"{document.repository_name}#{code_change.commit_sha}"
                cast(Any, document).commit_sha = unique_commit_sha

                # 메타데이터 업데이트 - 커밋 리스트에 추가
                new_commits = existing_commits + [commit_sha_str]
                updated_metadata = result.get("metadata", {})
                updated_metadata.update({
                    "commits": new_commits,
                    "commit_count": len(new_commits),
                    "last_updated": datetime.utcnow().isoformat(),
                    "latest_commit": str(code_change.commit_sha)
                })
                cast(Any, document).generation_metadata = updated_metadata  # type: ignore
                cast(Any, document).updated_at = datetime.utcnow()  # type: ignore

                session.commit()

                logger.info(f"Successfully appended commit {code_change.commit_sha} to document {document.id}")

                return {
                    "success": True,
                    "action": "appended",
                    "document_id": document.id,
                    "title": document.title,
                    "summary": document.summary,
                    "commit_count": len(new_commits)
                }
            else:
                # 실패한 경우 상태 복원
                cast(Any, document).status = "failed"  # type: ignore
                cast(Any, document).updated_at = datetime.utcnow()  # type: ignore

                session.commit()

                logger.error(f"Failed to append to document {document.id}: {result.get('error', 'Unknown error')}")

                return {
                    "success": False,
                    "action": "append_failed",
                    "document_id": document.id,
                    "error": result.get("error", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error appending to repository document: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Document append failed: {str(e)}"
            }

    async def _update_existing_document(self, session: Session, document: Document, code_change: CodeChange) -> Dict[
        str, Any]:
        """기존 문서 업데이트"""
        try:
            # 파일 변경사항 가져오기
            file_changes = session.query(FileChange).filter(
                FileChange.code_change_id == code_change.id
            ).all()

            logger.info(f"Updating document {document.id} with {len(file_changes)} file changes")

            # 상태를 updating으로 설정
            cast(Any, document).status = "updating"  # type: ignore
            cast(Any, document).updated_at = datetime.utcnow()  # type: ignore
            session.commit()

            # 생성기 입력 데이터 준비
            code_input = self._prepare_code_input(code_change, file_changes)

            # 문서 재생성
            result = await self.generator.generate_document(code_input)

            if result["success"]:
                # 기존 문서 업데이트
                document.title = result["title"]
                document.content = result["content"]
                document.summary = result.get("summary", "")
                cast(Any, document).status = "generated"  # type: ignore
                document.generation_metadata = result.get("metadata", {})
                cast(Any, document).updated_at = datetime.utcnow()  # type: ignore

                session.commit()

                logger.info(f"Successfully updated document {document.id}: {document.title}")

                return {
                    "success": True,
                    "action": "updated",
                    "document_id": document.id,
                    "title": document.title,
                    "summary": document.summary
                }
            else:
                # 업데이트 실패
                cast(Any, document).status = "failed"  # type: ignore
                document.generation_metadata = result.get("metadata", {})
                cast(Any, document).updated_at = datetime.utcnow()  # type: ignore

                session.commit()

                logger.error(f"Failed to update document {document.id}: {result.get('error', 'Unknown error')}")

                return {
                    "success": False,
                    "action": "update_failed",
                    "document_id": document.id,
                    "error": result.get("error", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error updating document: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Document update failed: {str(e)}"
            }

    def _prepare_code_input(self, code_change: CodeChange, file_changes: List[FileChange]) -> CodeChangeInput:
        """CodeChange 모델을 생성기 입력으로 변환"""
        files_data = []

        for file_change in file_changes:
            files_data.append({
                "filename": file_change.filename,
                "status": file_change.status,
                "changes": file_change.changes,
                "additions": file_change.additions,
                "deletions": file_change.deletions,
                "patch": file_change.patch or ""
            })

        # SQLAlchemy 모델 속성을 문자열로 안전하게 변환
        commit_sha = str(code_change.commit_sha) if code_change.commit_sha is not None else ""
        commit_message = str(code_change.commit_message) if code_change.commit_message is not None else ""
        author_name = str(code_change.author_name) if code_change.author_name is not None else "Unknown"
        repository_name = code_change.repository.full_name if code_change.repository else "unknown"
        total_changes = getattr(code_change, "total_changes", 0) if code_change.total_changes is not None else 0

        # timestamp 처리
        if code_change.timestamp is not None:
            timestamp = code_change.timestamp.isoformat()
        else:
            timestamp = datetime.utcnow().isoformat()

        return CodeChangeInput(
            commit_sha=commit_sha,
            commit_message=commit_message,
            author_name=author_name,
            repository_name=repository_name,
            timestamp=timestamp,
            files=files_data,
            total_changes=total_changes
        )

    def _prepare_cumulative_code_input(self, document: Document, code_change: CodeChange,
                                       file_changes: List[FileChange]) -> CodeChangeInput:
        """기존 문서 + 새 변경사항을 포함한 누적 입력 데이터 준비"""
        files_data = []

        # 새로운 파일 변경사항 추가
        for file_change in file_changes:
            files_data.append({
                "filename": file_change.filename,
                "status": file_change.status,
                "changes": file_change.changes,
                "additions": file_change.additions,
                "deletions": file_change.deletions,
                "patch": file_change.patch or ""
            })

        # 메타데이터에서 기존 커밋 정보 가져오기
        metadata = document.generation_metadata or {}
        existing_commits = metadata.get("commits", [])

        # 누적 커밋 메시지 생성 (기존 맥락 포함)
        cumulative_message = f"저장소 누적 업데이트 - 총 {len(existing_commits) + 1}개 커밋"
        commit_msg = str(code_change.commit_message) if code_change.commit_message is not None else ""
        if commit_msg:
            cumulative_message += f" | 최신: {commit_msg}"

        # 기존 커밋 맥락 추가
        if existing_commits:
            recent_commits = existing_commits[-3:] if len(existing_commits) > 3 else existing_commits
            cumulative_message += f" | 기존 커밋들: {', '.join(recent_commits)}"

        # 기존 문서 내용을 맥락으로 포함
        existing_content_summary = ""
        doc_content = str(document.content) if document.content is not None else ""
        if doc_content and len(doc_content) > 100:
            doc_summary = str(document.summary) if document.summary is not None else "요약 없음"
            existing_content_summary = f"기존 문서 요약: {doc_summary}\n\n"

        # SQLAlchemy 모델 속성을 문자열로 안전하게 변환
        commit_sha = str(code_change.commit_sha) if code_change.commit_sha is not None else ""
        author_name = str(code_change.author_name) if code_change.author_name is not None else "Unknown"
        repository_name = str(document.repository_name) if document.repository_name is not None else "unknown"
        total_changes = getattr(code_change, "total_changes", 0) if code_change.total_changes is not None else 0

        # timestamp 처리
        if code_change.timestamp is not None:
            timestamp = code_change.timestamp.isoformat()
        else:
            timestamp = datetime.utcnow().isoformat()

        return CodeChangeInput(
            commit_sha=commit_sha,
            commit_message=cumulative_message,
            author_name=author_name,
            repository_name=repository_name,
            timestamp=timestamp,
            files=files_data,
            total_changes=total_changes
        )

    def get_documents(self, repository_name: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[
        Dict[str, Any]]:
        """문서 목록 조회"""
        session = SessionLocal()
        try:
            query = session.query(Document)

            if repository_name:
                query = query.filter(Document.repository_name == repository_name)

            documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

            result = []
            for doc in documents:
                # None 체크를 통한 안전한 변환
                created_at = doc.created_at.isoformat() if doc.created_at is not None else None
                updated_at = doc.updated_at.isoformat() if doc.updated_at is not None else None

                result.append({
                    "id": doc.id,
                    "title": doc.title,
                    "summary": doc.summary,
                    "status": doc.status,
                    "commit_sha": doc.commit_sha,
                    "repository_name": doc.repository_name,
                    "created_at": created_at,
                    "updated_at": updated_at
                })

            return result
        finally:
            session.close()

    def get_document_detail(self, document_id: int) -> Optional[Dict[str, Any]]:
        """문서 상세 조회"""
        session = SessionLocal()
        try:
            document = session.query(Document).filter(Document.id == document_id).first()

            if not document:
                return None

            # None 체크를 통한 안전한 변환
            created_at = document.created_at.isoformat() if document.created_at is not None else None
            updated_at = document.updated_at.isoformat() if document.updated_at is not None else None

            return {
                "id": document.id,
                "title": document.title,
                "content": document.content,
                "summary": document.summary,
                "status": document.status,
                "document_type": document.document_type,
                "commit_sha": document.commit_sha,
                "repository_name": document.repository_name,
                "generation_metadata": document.generation_metadata,
                "created_at": created_at,
                "updated_at": updated_at,
                "code_change_id": document.code_change_id
            }
        finally:
            session.close()

    async def regenerate_document(self, document_id: int) -> Dict[str, Any]:
        """기존 문서 재생성"""
        session = SessionLocal()
        try:
            document = session.query(Document).filter(Document.id == document_id).first()

            if not document:
                return {
                    "success": False,
                    "error": f"Document not found: {document_id}"
                }

            # 연관된 코드 변경사항 찾기
            code_change = session.query(CodeChange).filter(
                CodeChange.id == document.code_change_id
            ).first()

            if not code_change:
                return {
                    "success": False,
                    "error": f"Associated code change not found for document: {document_id}"
                }

            logger.info(f"Regenerating document {document_id} for code change {code_change.id}")

            # 기존 문서 업데이트 로직 사용
            return await self._update_existing_document(session, document, code_change)

        except Exception as e:
            logger.error(f"Error regenerating document {document_id}: {str(e)}", exc_info=True)
            session.rollback()
            return {
                "success": False,
                "error": f"Document regeneration failed: {str(e)}"
            }
        finally:
            session.close()


# 전역 서비스 인스턴스
_service_instance: Optional[DocumentService] = None


def get_document_service(use_mock: bool = True) -> DocumentService:
    """문서 서비스 싱글톤 인스턴스 반환"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DocumentService(use_mock=use_mock)
    return _service_instance


def reset_document_service():
    """서비스 인스턴스 리셋 (테스트용)"""
    global _service_instance
    _service_instance = None
