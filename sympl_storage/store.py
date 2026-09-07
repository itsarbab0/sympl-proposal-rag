"""
Sympl Solutions Proposal RAG — Artifact Storage Layer

Provides abstracted storage interfaces and implementations for saving generated proposal
artifacts (plans, drafts, and rendered outputs) locally or to cloud object stores (S3).
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class ArtifactStore(ABC):
    """Abstract storage interface for proposal artifacts."""

    @abstractmethod
    def save_plan(self, proposal_id: str, plan_dict: Dict[str, Any]) -> str:
        """Persists proposal_plan.json and returns uri/path."""
        pass

    @abstractmethod
    def save_draft(self, proposal_id: str, draft_dict: Dict[str, Any]) -> str:
        """Persists proposal_draft.json and returns uri/path."""
        pass

    @abstractmethod
    def save_render(self, proposal_id: str, render_dict: Dict[str, Any]) -> str:
        """Persists rendered_proposal.json and returns uri/path."""
        pass

    @abstractmethod
    def load_plan(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Loads proposal_plan.json for a given proposal_id."""
        pass

    @abstractmethod
    def load_draft(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Loads proposal_draft.json for a given proposal_id."""
        pass

    @abstractmethod
    def load_render(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Loads rendered_proposal.json for a given proposal_id."""
        pass

    @abstractmethod
    def save_intake(self, job_id: str, intake: Dict[str, Any]) -> str:
        """Persists intake payload for a job and returns uri/path."""
        pass

    @abstractmethod
    def load_intake(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Loads intake payload for a given job_id."""
        pass


class LocalArtifactStore(ArtifactStore):
    """Local filesystem implementation storing artifacts under a base directory."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            env_dir = os.getenv("STORAGE_DIR")
            if env_dir:
                self.base_dir = Path(env_dir)
            else:
                self.base_dir = Path(__file__).resolve().parent.parent / "data" / "proposals"
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _proposal_dir(self, proposal_id: str) -> Path:
        p_dir = self.base_dir / proposal_id
        p_dir.mkdir(parents=True, exist_ok=True)
        return p_dir

    def save_plan(self, proposal_id: str, plan_dict: Dict[str, Any]) -> str:
        target = self._proposal_dir(proposal_id) / "proposal_plan.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2, ensure_ascii=False)
        return str(target)

    def save_draft(self, proposal_id: str, draft_dict: Dict[str, Any]) -> str:
        target = self._proposal_dir(proposal_id) / "proposal_draft.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(draft_dict, f, indent=2, ensure_ascii=False)
        return str(target)

    def save_render(self, proposal_id: str, render_dict: Dict[str, Any]) -> str:
        target = self._proposal_dir(proposal_id) / "rendered_proposal.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(render_dict, f, indent=2, ensure_ascii=False)
        return str(target)

    def load_plan(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        target = self._proposal_dir(proposal_id) / "proposal_plan.json"
        if not target.exists():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_draft(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        target = self._proposal_dir(proposal_id) / "proposal_draft.json"
        if not target.exists():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_render(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        target = self._proposal_dir(proposal_id) / "rendered_proposal.json"
        if not target.exists():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_intake(self, job_id: str, intake: Dict[str, Any]) -> str:
        job_dir = self.base_dir / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        target = job_dir / "intake.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(intake, f, indent=2, ensure_ascii=False)
        return str(target)

    def load_intake(self, job_id: str) -> Optional[Dict[str, Any]]:
        target = self.base_dir / "jobs" / job_id / "intake.json"
        if not target.exists():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)


class S3ArtifactStore(ArtifactStore):
    """
    Prepared cloud object store interface for AWS S3 / Cloudflare R2.
    Implemented as a ready architectural extension point.
    """

    def __init__(self, bucket_name: str, prefix: str = "proposals/"):
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")

    def save_plan(self, proposal_id: str, plan_dict: Dict[str, Any]) -> str:
        key = f"{self.prefix}/{proposal_id}/proposal_plan.json"
        return f"s3://{self.bucket_name}/{key}"

    def save_draft(self, proposal_id: str, draft_dict: Dict[str, Any]) -> str:
        key = f"{self.prefix}/{proposal_id}/proposal_draft.json"
        return f"s3://{self.bucket_name}/{key}"

    def save_render(self, proposal_id: str, render_dict: Dict[str, Any]) -> str:
        key = f"{self.prefix}/{proposal_id}/rendered_proposal.json"
        return f"s3://{self.bucket_name}/{key}"

    def load_plan(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return None

    def load_draft(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return None

    def load_render(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return None

    def save_intake(self, job_id: str, intake: Dict[str, Any]) -> str:
        key = f"{self.prefix}/jobs/{job_id}/intake.json"
        return f"s3://{self.bucket_name}/{key}"

    def load_intake(self, job_id: str) -> Optional[Dict[str, Any]]:
        return None


# Default shared instance
default_store = LocalArtifactStore()
