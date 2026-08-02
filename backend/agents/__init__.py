"""
agents/ — Research Mode multi-agent pipeline.

Agents (defined in crew_runner.py, implemented as async Python functions):
  OrchestratorAgent  — Plans which crew to assemble based on query + history
  ResearchAgent      — Multi-hop RAG retrieval from transcript_chunks
  WriterAgent        — Streams QA answers or Ship30for30 essays
  ArtifactAgent      — Generates interactive HTML dashboards
  ValidatorAgent     — QC + self-healing for broken artifacts or thin essays
"""
