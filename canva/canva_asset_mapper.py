"""
Sympl Solutions — Canva Asset Mapper
Manages template asset cleanup, logo replacements, and client-specific image fills.
"""

from typing import List, Dict, Any, Optional
from .models import CanvaEditingOperation, CanvaOperationType


class CanvaAssetMapper:
    """
    Handles asset and fill lifecycle for Canva templates.
    Specifically ensures template-specific placeholder graphics (such as artist signatures)
    are cleaned up or replaced with legitimate client assets.
    """

    # Template DAHU1H8DMjc known assets
    COVER_CLIENT_ARTWORK_ELEMENT_ID = "PBV1SCndGVxlSNHy-LB1cLWqpGhNmsF2c"
    SYMPL_LOGO_COVER_ELEMENT_ID = "PBV1SCndGVxlSNHy-LBQ6fpWK1jvZ4FHk"
    SYMPL_LOGO_FOOTER_ASSET_ID = "MAHLbOC6BpM"

    def __init__(self, template_id: str = "DAHU1H8DMjc"):
        self.template_id = template_id

    def generate_asset_operations(
        self,
        client_name: str,
        client_assets: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates editing operations for media elements:
        - Removes template-specific placeholder artwork if no replacement is supplied.
        - Replaces with client logo/artwork if an asset_id is provided.
        - Preserves official Sympl branding logos.
        """
        operations: List[CanvaEditingOperation] = []
        client_assets = client_assets or {}

        # 1. Handle Cover Page Client Artwork / Signature
        cover_artwork_asset = client_assets.get("cover_artwork") or client_assets.get("logo")
        if cover_artwork_asset:
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.UPDATE_FILL,
                element_id=self.COVER_CLIENT_ARTWORK_ELEMENT_ID,
                asset_id=cover_artwork_asset,
                asset_type="image",
                alt_text=f"{client_name} Logo / Cover Asset"
            ))
        else:
            # Delete the Gary Crawford watercolor artwork so the title area is pristine
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.DELETE_ELEMENT,
                element_id=self.COVER_CLIENT_ARTWORK_ELEMENT_ID
            ))

        return [op.to_dict() for op in operations]
