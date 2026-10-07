"""Persistent, inspectable scientific research state. Provider records are not LLM inventions."""
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class ResearchAuthor(Strict):
    family: str = Field('', max_length=200)
    given: str = Field('', max_length=200)
    literal: str = Field('', max_length=400)

class ScholarlyMeta(Strict):
    title: str = Field(max_length=2000)
    authors: list[ResearchAuthor] = Field(default_factory=list, max_length=3000)
    year: int | None = Field(None, ge=1400, le=2200)
    journal: str = Field('', max_length=600)
    volume: str = Field('', max_length=100)
    issue: str = Field('', max_length=100)
    pages: str = Field('', max_length=150)
    doi: str = Field('', max_length=300)
    pmid: str = Field('', max_length=40)
    pmcid: str = Field('', max_length=40)
    arxiv_id: str = Field('', max_length=100)
    url: str = Field('', max_length=2000)
    fulltext_url: str = Field('', max_length=2000)
    publication_type: str = Field('', max_length=400)
    reference_override: str = Field('', max_length=6000)
    preprint: bool = False
    retracted: bool = False
    metadata_sources: list[str] = Field(default_factory=list)
    retrieved_at: str = ''
    content_scope: Literal['metadata', 'abstract', 'full_text', 'user_supplied'] = 'metadata'

class ResearchRecord(Strict):
    id: str
    metadata: ScholarlyMeta
    abstract: str = Field('', max_length=100000)
    decision: Literal['unscreened', 'include', 'exclude'] = 'unscreened'
    reason: str = Field('', max_length=3000)
    source_id: str = ''
    searches: list[str] = Field(default_factory=list)
    appraisal: dict[str, Any] = Field(default_factory=dict)
    appraisal_source_hash: str = ''
    fulltext_error: str = ''

class ResearchPlan(Strict):
    question: str = Field('', max_length=4000)
    article_type: Literal['narrative_review', 'scoping_review', 'systematic_review', 'protocol', 'empirical'] = 'narrative_review'
    queries: list[str] = Field(default_factory=list, max_length=6)
    database_queries: dict[str, str] = Field(default_factory=dict)
    databases: list[Literal['pubmed','semantic_scholar','arxiv','crossref','europe_pmc']] = Field(default_factory=lambda:['pubmed','semantic_scholar','arxiv','crossref'])
    year_from: int | None = Field(None, ge=1400, le=2200)
    year_to: int | None = Field(None, ge=1400, le=2200)
    per_database: int = Field(20, ge=1, le=100)
    inclusion: str = Field('', max_length=6000)
    exclusion: str = Field('', max_length=6000)
    population: str = Field('', max_length=1000)
    intervention: str = Field('', max_length=1000)
    comparator: str = Field('', max_length=1000)
    outcomes: str = Field('', max_length=2000)
    preregistration: str = Field('', max_length=2000)
    preprints: bool = True
    fulltext_required: bool = False
    author_names: str = Field('', max_length=2000)
    affiliation: str = Field('', max_length=2000)
    running_head: str = Field('', max_length=50)
    author_note: str = Field('', max_length=6000)
    funding: str = Field('', max_length=3000)
    conflicts: str = Field('', max_length=3000)
    data_availability: str = Field('', max_length=3000)
    ethics: str = Field('', max_length=3000)
    ai_disclosure: str = Field('AI tools assisted with literature organization and drafting. The named authors must verify all claims and references before submission.', max_length=4000)
    journal_requirements: str = Field('', max_length=6000)
    empirical_results_source_ids: list[str] = Field(default_factory=list)
    @model_validator(mode='after')
    def validate_plan(self):
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError('Start year must not exceed end year.')
        if any(len(q) > 2000 for q in self.queries) or any(len(q) > 4000 for q in self.database_queries.values()):
            raise ValueError('Search query exceeds its length limit.')
        self.databases = list(dict.fromkeys(self.databases))
        return self

class ResearchWorkspace(Strict):
    plan: ResearchPlan = Field(default_factory=ResearchPlan)
    records: list[ResearchRecord] = Field(default_factory=list, max_length=600)
    searches: list[dict[str, Any]] = Field(default_factory=list, max_length=300)
    abstract: str = Field('', max_length=12000)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    synthesis: dict[str, Any] = Field(default_factory=dict)
    readiness: dict[str, Any] = Field(default_factory=dict)
    manuscript_fingerprint: str = ''
    acknowledgements: dict[str, bool] = Field(default_factory=dict)
    confirmation_hash: str = ''
