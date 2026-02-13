"""
Files preview module
3D model preview generation service

This service is responsible for:
- Receiving a 3D model file path (already saved locally)
- Calling CALCULATOR_BASE_URL to generate preview PNGs
- Persisting the final preview PNG(s) to PREVIEW_DIR

CadQuery is NOT required here anymore; it lives in the calculator service.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import base64
import httpx
from PIL import Image, ImageDraw, ImageFont

from backend.core.config import CALCULATOR_BASE_URL, PREVIEW_DIR

logger = logging.getLogger(__name__)


class PreviewGenerator:
    """3D model preview generation client (delegates rendering to calculator service)."""

    def __init__(self, preview_dir: str = None):
        if preview_dir is None:
            preview_dir = PREVIEW_DIR

        self.preview_dir = Path(preview_dir)
        self.preview_dir.mkdir(parents=True, exist_ok=True)

        # Preview settings
        self.preview_size = (512, 512)
        self.supported_formats = {".stl", ".stp", ".step"}

    def _generate_preview_filename(self, original_filename: str) -> str:
        """Generate unique preview filename"""
        file_stem = Path(original_filename).stem
        unique_id = str(uuid.uuid4())[:8]
        return f"{file_stem}_{unique_id}_preview.png"

    async def generate_preview(self, model_path: Path, original_filename: str) -> Optional[Dict[str, Any]]:
        """
        Generate preview image 
        for given model_path and persist it into PREVIEW_DIR.
        """
        try:
            ext = Path(model_path).suffix.lower()
            if ext not in self.supported_formats:
                logger.warning(f"Unsupported file format for preview: {ext}")
                return {
                    "preview_filename": None,
                    "preview_path": None,
                    "preview_generated": False,
                    "preview_generation_error": f"Unsupported file format: {ext}",
                }

            preview_filename = self._generate_preview_filename(original_filename)
            preview_path = self.preview_dir / preview_filename

            ok = await self._generate_via_calculator(model_path, original_filename, preview_path)
            if not ok:
                logger.warning(f"Remote preview generation failed for {original_filename}, using placeholder")
                await self._generate_placeholder_preview(preview_path, original_filename)

            return {
                "preview_filename": preview_filename if preview_path.exists() else None,
                "preview_path": str(preview_path) if preview_path.exists() else None,
                "preview_generated": preview_path.exists(),
                "preview_generation_error": None if preview_path.exists() else "Preview generation failed",
            }

        except Exception as e:
            logger.exception(f"Error generating preview for {original_filename}")
            return {
                "preview_filename": None,
                "preview_path": None,
                "preview_generated": False,
                "preview_generation_error": str(e),
            }

    async def _generate_via_calculator(self, model_path: Path, original_filename: str, preview_path: Path) -> bool:
        """Call calculator service /generate-previews and save the first returned PNG."""
        url = f"{CALCULATOR_BASE_URL}/generate-previews"

        if not CALCULATOR_BASE_URL:
            logger.warning("Calculator service URL not configured, skipping calculator call")
            return False

        params = {
            "size": self.preview_size[0],
            "views": 1,
        }

        # timeout = httpx.Timeout(connect=50.0, read=120.0, write=120.0, pool=50.0)

        async with httpx.AsyncClient(timeout=50) as client:
            with open(model_path, "rb") as f:
                files = {"file": (original_filename, f, "application/octet-stream")}
                resp = await client.post(url, params=params, files=files)
        logger.info("post is made")

        if resp.status_code >= 400:
            logger.warning(f"Calculator preview endpoint error {resp.status_code}: {resp.text[:500]}")
            return False

        try:
            payload = resp.json()
        except Exception:
            logger.warning("Calculator preview endpoint returned non-JSON response")
            return False

        # ResponseWrapper may wrap payload into {success,data,...}; handle both.
        data = payload.get("data") if isinstance(payload, dict) else None
        if not data and isinstance(payload, dict):
            data = payload  # fallback

        images = (data or {}).get("images_png_base64") or []
        if not images:
            logger.warning(f"No images in calculator response: keys={list((data or {}).keys())}")
            return False

        try:
            png_bytes = base64.b64decode(images[0])
            with open(preview_path, "wb") as out:
                out.write(png_bytes)
            logger.info("png is saved")
            return preview_path.exists() and preview_path.stat().st_size > 0
        except Exception as e:
            logger.warning(f"Failed to decode/save PNG from calculator: {e}")
            return False

    async def _generate_placeholder_preview(self, preview_path: Path, original_filename: str) -> bool:
        """Generate a simple local placeholder PNG."""
        try:
            img = Image.new("RGB", self.preview_size, color=(240, 240, 240))
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("arial.ttf", 18)
            except Exception:
                font = ImageFont.load_default()

            text = f"{Path(original_filename).suffix.upper()}\npreview unavailable"
            bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=6, align="center")
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            x = (self.preview_size[0] - tw) // 2
            y = (self.preview_size[1] - th) // 2
            draw.multiline_text((x, y), text, fill=(0, 0, 0), font=font, spacing=6, align="center")

            img.save(str(preview_path), "PNG")
            return True
        except Exception as e:
            logger.warning(f"Error generating placeholder preview: {e}")
            return False

    def get_preview_path(self, preview_filename: str) -> Optional[Path]:
        if not preview_filename:
            return None
        p = self.preview_dir / preview_filename
        return p if p.exists() else None


# Global instance
preview_generator = PreviewGenerator()
