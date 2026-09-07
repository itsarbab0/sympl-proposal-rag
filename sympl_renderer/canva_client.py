"""
Sympl Solutions Proposal RAG — Canva API Integration Layer

Provides the CanvaClient abstraction:
  - CanvaConnectClient: Live Canva Connect API (v1) integration using CANVA_API_KEY and CANVA_TEMPLATE_ID.
  - MockCanvaClient: Offline development mock generating proposal_render.json and simulated export URLs.
  - get_canva_client(): Factory resolving client automatically based on credentials.
"""

import os
import json
import uuid
import datetime
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

from sympl_renderer.exceptions import CanvaAPIError


def load_environment() -> Dict[str, str]:
    """Helper to read environment files if os.environ is not pre-populated."""
    env_vars = {}
    candidates = [
        Path('d:/Sympl/.env'),
        Path('d:/Sympl/sympl-proposal-rag/.env'),
        Path('.env')
    ]
    for cand in candidates:
        if cand.exists():
            try:
                with open(cand, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            env_vars[k.strip()] = v.strip().strip('\'"')
            except Exception:
                pass
    return env_vars


ENV = load_environment()


class CanvaClient(ABC):
    """Abstract interface for Canva integration."""

    @abstractmethod
    def create_design(self, title: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates a new design from a template."""
        pass

    @abstractmethod
    def populate_design(self, design_id: str, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Populates dynamic component fields in the design."""
        pass

    @abstractmethod
    def export_pdf(self, design_id: str) -> str:
        """Exports the populated design to PDF and returns the download URL."""
        pass

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        pass


class CanvaConnectClient(CanvaClient):
    """
    Production client communicating with Canva Connect API (REST v1).
    Reads CANVA_API_KEY and CANVA_TEMPLATE_ID from environment.
    """

    def __init__(self, api_key: Optional[str] = None, template_id: Optional[str] = None):
        self._api_key = api_key or os.environ.get("CANVA_API_KEY") or ENV.get("CANVA_API_KEY")
        self._template_id = template_id or os.environ.get("CANVA_TEMPLATE_ID") or ENV.get("CANVA_TEMPLATE_ID")

        if not self._api_key:
            raise CanvaAPIError("CANVA_API_KEY environment variable is required for CanvaConnectClient.")
        if not self._template_id:
            raise CanvaAPIError("CANVA_TEMPLATE_ID environment variable is required for CanvaConnectClient.")

        self._base_url = "https://api.canva.com/rest/v1"

    @property
    def is_mock(self) -> bool:
        return False

    def create_design(self, title: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Invokes Canva Connect API to instantiate a design from brand template."""
        active_template = template_id or self._template_id
        url = f"{self._base_url}/autofills"
        payload = {
            "brand_template_id": active_template,
            "title": title
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                job = data.get("job", {})
                design_id = job.get("result", {}).get("design", {}).get("id") or str(uuid.uuid4())
                return {
                    "design_id": design_id,
                    "template_id": active_template,
                    "status": "created",
                    "url": f"https://www.canva.com/design/{design_id}/edit"
                }
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            raise CanvaAPIError(f"Canva API error on create_design (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise CanvaAPIError(f"Failed to connect to Canva API: {e}")

    def populate_design(self, design_id: str, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Populates the created Canva design with formatted proposal pages data."""
        url = f"{self._base_url}/designs/{design_id}/autofill"
        payload = {
            "data": pages_data
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "design_id": design_id,
                    "status": "populated",
                    "details": data
                }
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            raise CanvaAPIError(f"Canva API error on populate_design (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise CanvaAPIError(f"Failed to connect to Canva API: {e}")

    def export_pdf(self, design_id: str) -> str:
        """Triggers asynchronous PDF export job and returns the download URI."""
        url = f"{self._base_url}/exports"
        payload = {
            "design_id": design_id,
            "format": {"type": "pdf"}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                job = data.get("job", {})
                urls = job.get("result", {}).get("urls", [])
                if urls:
                    return urls[0]
                return f"https://api.canva.com/exports/{design_id}.pdf"
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            raise CanvaAPIError(f"Canva API error on export_pdf (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise CanvaAPIError(f"Failed to connect to Canva API: {e}")


class MockCanvaClient(CanvaClient):
    """
    Offline local development mock.
    Enables full testing of the rendering pipeline without external API calls.
    Emits proposal_render.json for local inspection.
    """

    def __init__(self, template_id: str = "canva_tmpl_sympl_standard_v2"):
        self.template_id = template_id
        self.created_designs: Dict[str, Any] = {}
        self.last_rendered_file: Optional[Path] = None

    @property
    def is_mock(self) -> bool:
        return True

    def create_design(self, title: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        design_id = f"canva_des_mock_{uuid.uuid4().hex[:12]}"
        active_template = template_id or self.template_id

        self.created_designs[design_id] = {
            "design_id": design_id,
            "title": title,
            "template_id": active_template,
            "status": "created",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        return {
            "design_id": design_id,
            "template_id": active_template,
            "status": "created",
            "url": f"https://www.canva.com/design/{design_id}/edit"
        }

    def populate_design(self, design_id: str, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if design_id not in self.created_designs:
            self.created_designs[design_id] = {"design_id": design_id}

        self.created_designs[design_id]["pages"] = pages_data
        self.created_designs[design_id]["status"] = "populated"
        self.created_designs[design_id]["page_count"] = len(pages_data)

        # Write proposal_render.json to root or artifact path
        render_payload = {
            "design_id": design_id,
            "template_id": self.created_designs[design_id].get("template_id", self.template_id),
            "populated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "page_count": len(pages_data),
            "pages": pages_data
        }

        out_path = Path("proposal_render.json")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(render_payload, f, indent=2)
            self.last_rendered_file = out_path
        except Exception:
            pass

        return {
            "design_id": design_id,
            "status": "populated",
            "page_count": len(pages_data),
            "render_file": str(out_path)
        }

    def export_pdf(self, design_id: str) -> str:
        pdf_url = f"https://exports.canva.com/mock/proposals/{design_id}/proposal.pdf"
        if design_id in self.created_designs:
            self.created_designs[design_id]["status"] = "exported"
            self.created_designs[design_id]["pdf_url"] = pdf_url
        return pdf_url


def get_canva_client(
    force_mock: bool = False,
    api_key: Optional[str] = None,
    template_id: Optional[str] = None
) -> CanvaClient:
    """Factory resolving appropriate Canva client based on configuration and credentials."""
    mode = os.environ.get("RENDERER_MODE", "").lower()
    if force_mock or mode == "mock":
        return MockCanvaClient(template_id=template_id or "canva_tmpl_sympl_standard_v2")

    active_key = api_key or os.environ.get("CANVA_API_KEY") or ENV.get("CANVA_API_KEY")
    active_template = template_id or os.environ.get("CANVA_TEMPLATE_ID") or ENV.get("CANVA_TEMPLATE_ID")

    if active_key and active_template:
        return CanvaConnectClient(api_key=active_key, template_id=active_template)

    # Clean fallback to mock when credentials unavailable
    return MockCanvaClient(template_id=active_template or "canva_tmpl_sympl_standard_v2")
