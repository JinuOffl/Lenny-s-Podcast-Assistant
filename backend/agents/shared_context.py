"""
agents/shared_context.py — Shared state dataclass passed between all agents.

Each agent reads from SharedContext and writes its output back to it.
This acts as the "working memory" of the Research Mode pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class ExecutionPlan:
    """OrchestratorAgent's output — the research plan."""
    needs_essay: bool = False
    needs_artifact: bool = False
    needs_qa: bool = True
    complexity: str = "simple"          # "simple" | "deep" | "multi"
    primary_search_query: str = ""      # refined search query for ResearchAgent
    secondary_search_query: str = ""    # optional second search for multi-hop
    crew_type: str = "qa"               # "qa" | "essay" | "full_research"
    reasoning: str = ""                 # Orchestrator's reasoning (shown in UI)


@dataclass
class SharedContext:
    """
    Mutable working memory shared across all pipeline stages.

    Lifecycle:
      1. Orchestrator fills the ExecutionPlan fields
      2. ResearchAgent fills chunks / sources / context_text
      3. WriterAgent fills primary_response / skill_used
      4. ArtifactAgent fills artifact (if needed)
      5. ValidatorAgent validates and may trigger self-healing
    """
    # Request context (set at start, never modified)
    session_id: str = ""
    user_query: str = ""
    history: List[Dict] = field(default_factory=list)

    # ── Orchestrator plan ─────────────────────────────────────────────────────
    plan: ExecutionPlan = field(default_factory=ExecutionPlan)

    # ── Research phase output ─────────────────────────────────────────────────
    chunks: List[Dict] = field(default_factory=list)
    sources: List[Dict] = field(default_factory=list)
    context_text: str = ""
    research_summary: str = ""  # ResearchAgent's synthesis of what it found
    episodes_searched: int = 0
    search_hops: int = 0        # How many times ResearchAgent searched

    # ── Writing phase output ──────────────────────────────────────────────────
    primary_response: str = ""
    skill_used: str = "qa"      # "qa" | "ship30for30" | "multi" | "followup"

    # ── Artifact phase output ─────────────────────────────────────────────────
    artifact: Optional[Dict] = None   # {"type": "html"|"markdown", "content": "..."}

    # ── Validator / self-healing ──────────────────────────────────────────────
    heal_attempts: int = 0
    heal_errors: List[str] = field(default_factory=list)
    validation_passed: bool = True
    confidence: str = "high"    # "high" | "medium" | "low"
    word_count: int = 0

    # ── Agent trace (for UI AgentTracker + logs) ──────────────────────────────
    agent_steps: List[Dict] = field(default_factory=list)

    def add_step(self, agent: str, step: str) -> None:
        """Record an agent step for tracing."""
        self.agent_steps.append({"agent": agent, "step": step})

    def compute_confidence(self) -> str:
        """Auto-compute confidence based on source count."""
        n = len(self.sources)
        if n >= 5:
            return "high"
        elif n >= 2:
            return "medium"
        else:
            return "low"
