# File Summarizer LLM 테스트 결과

**테스트 일시**: 2025-11-22 01:21:36

## 📊 전체 통계

- **테스트 파일 수**: 5개
- **평균 품질 점수**: 20.0/100
- **평균 등급**: D

## 📁 파일별 상세 결과

### 1. main.py

- **언어**: python
- **생성 방식**: llm
- **품질 점수**: 20/100 (D)

#### 📝 요약 내용

**목적**: Unknown

**역할**: Unknown

**주요 기능**:
- Initializes FastAPI application
- Configures CORS middleware
- Includes routers for user and document functionalities

#### 📊 통계 정보

- 함수: 0개
- 클래스: 0개
- 임포트: 0개
- LOC: 34줄

#### ✅ 장점

- 3개의 주요 기능 식별됨

#### ⚠️ 개선점

- 누락된 필드: ['purpose', 'role']
- 목적 설명이 너무 간단함
- 복잡도 평가가 누락됨
- 의존성 분석이 누락됨
- 유지보수성 평가가 누락됨

---

### 2. models.py

- **언어**: python
- **생성 방식**: llm
- **품질 점수**: 20/100 (D)

#### 📝 요약 내용

**목적**: Unknown

**역할**: Unknown

**주요 기능**:
- Defines relationships between models using SQLAlchemy ORM.
- Includes fields for storing GitHub user and repository information.
- Handles webhook registrations and code change tracking.

#### 📊 통계 정보

- 함수: 0개
- 클래스: 0개
- 임포트: 0개
- LOC: 110줄

#### ✅ 장점

- 3개의 주요 기능 식별됨

#### ⚠️ 개선점

- 누락된 필드: ['purpose', 'role']
- 목적 설명이 너무 간단함
- 복잡도 평가가 누락됨
- 의존성 분석이 누락됨
- 유지보수성 평가가 누락됨

---

### 3. domain/langgraph/nodes/file_summarizer_node.py

- **언어**: python
- **생성 방식**: llm
- **품질 점수**: 20/100 (D)

#### 📝 요약 내용

**목적**: Unknown

**역할**: Unknown

**주요 기능**:
- 파일 요약 생성 기능
- 환경 변수 기반 설정
- Mock 및 LLM 전략 선택 기능

#### 📊 통계 정보

- 함수: 0개
- 클래스: 0개
- 임포트: 0개
- LOC: 361줄

#### ✅ 장점

- 3개의 주요 기능 식별됨

#### ⚠️ 개선점

- 누락된 필드: ['purpose', 'role']
- 목적 설명이 너무 간단함
- 복잡도 평가가 누락됨
- 의존성 분석이 누락됨
- 유지보수성 평가가 누락됨

---

### 4. domain/langgraph/nodes/file_parser_node.py

- **언어**: python
- **생성 방식**: llm
- **품질 점수**: 20/100 (D)

#### 📝 요약 내용

**목적**: Unknown

**역할**: Unknown

**주요 기능**:
- Uses Tree-sitter for parsing when available, with fallbacks for different languages.
- Provides a mock mode for testing without actual file parsing.
- Handles errors gracefully and maintains the state of the parsing process.

#### 📊 통계 정보

- 함수: 0개
- 클래스: 0개
- 임포트: 0개
- LOC: 104줄

#### ✅ 장점

- 3개의 주요 기능 식별됨

#### ⚠️ 개선점

- 누락된 필드: ['purpose', 'role']
- 목적 설명이 너무 간단함
- 복잡도 평가가 누락됨
- 의존성 분석이 누락됨
- 유지보수성 평가가 누락됨

---

### 5. domain/langgraph/document_service.py

- **언어**: python
- **생성 방식**: llm
- **품질 점수**: 20/100 (D)

#### 📝 요약 내용

**목적**: Unknown

**역할**: Unknown

**주요 기능**:
- Asynchronous processing of code changes
- Integration with OpenAI API for document generation
- Mock response capability for testing and development

#### 📊 통계 정보

- 함수: 0개
- 클래스: 0개
- 임포트: 0개
- LOC: 73줄

#### ✅ 장점

- 3개의 주요 기능 식별됨

#### ⚠️ 개선점

- 누락된 필드: ['purpose', 'role']
- 목적 설명이 너무 간단함
- 복잡도 평가가 누락됨
- 의존성 분석이 누락됨
- 유지보수성 평가가 누락됨

---

