from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class SourceInfo(BaseModel):
    type: str  # "filing" or "financial_metric"
    company: str
    year: int
    detail: str  # section name or metric name


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[str]
    sources: list[SourceInfo]


class DocumentIngestRequest(BaseModel):
    company: str
    year: int
    document_type: str
    stage_path: str
    source_filename: str


class DocumentIngestResponse(BaseModel):
    document_id: str
    chunks_ingested: int


class DocumentInfo(BaseModel):
    document_id: str
    company: str
    year: int
    document_type: str | None
    source_filename: str | None


class HealthResponse(BaseModel):
    status: str
