"""
Files preview module
3D model preview generation service
"""
import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import io

logger = logging.getLogger(__name__)

class PreviewGenerator:
    """3D model preview generation service using trimesh and pyvista"""
    
    def __init__(self, preview_dir: str = None):
        if preview_dir is None:
            preview_dir = os.getenv("PREVIEW_DIR", "uploads/previews")
        
        self.preview_dir = Path(preview_dir)
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        
        # Preview generation settings
        self.preview_size = (512, 512)
        self.background_color = (240, 240, 240)
        self.supported_formats = {'.stl', '.obj', '.ply', '.3ds', '.dae', '.fbx', '.blend', '.stp', '.step'}
    
    def _generate_preview_filename(self, original_filename: str) -> str:
        """Generate unique preview filename"""
        file_stem = Path(original_filename).stem
        unique_id = str(uuid.uuid4())[:8]
        return f"{file_stem}_{unique_id}_preview.png"
    
    async def generate_preview(self, model_path: Path, original_filename: str) -> Optional[Dict[str, Any]]:
        """Generate preview image from 3D model file"""
        try:
            # Check if file format is supported
            file_extension = Path(model_path).suffix.lower()
            if file_extension not in self.supported_formats:
                logger.warning(f"Unsupported file format for preview: {file_extension}")
                return None
            
            # Generate preview filename and path
            preview_filename = self._generate_preview_filename(original_filename)
            preview_path = self.preview_dir / preview_filename
            
            # Try different preview generation methods
            success = False
            
            # Method 1: Try trimesh (lightweight, good for STL/OBJ)
            if file_extension in {'.stl', '.obj', '.ply'}:
                try:
                    success = await self._generate_with_trimesh(model_path, preview_path)
                    if success:
                        logger.info(f"Preview generated with trimesh: {preview_filename}")
                except Exception as e:
                    logger.warning(f"Trimesh preview generation failed: {e}")
            
            # Method 2: Try STEP reader (for STP/STEP files)
            if not success and file_extension in {'.stp', '.step'}:
                try:
                    success = await self._generate_with_step_reader(model_path, preview_path)
                    if success:
                        logger.info(f"Preview generated with STEP reader: {preview_filename}")
                except Exception as e:
                    logger.warning(f"STEP reader preview generation failed: {e}")
            
            # Method 3: Try pyvista (more powerful, supports more formats)
            if not success:
                try:
                    success = await self._generate_with_pyvista(model_path, preview_path)
                    if success:
                        logger.info(f"Preview generated with pyvista: {preview_filename}")
                except Exception as e:
                    logger.warning(f"Pyvista preview generation failed: {e}")
            
            # Method 3: Fallback to placeholder
            if not success:
                logger.warning(f"All preview generation methods failed for {original_filename}, using placeholder")
                success = await self._generate_placeholder_preview(preview_path, original_filename)
            
            if success and preview_path.exists():
                return {
                    "preview_filename": preview_filename,
                    "preview_path": str(preview_path),
                    "preview_generated": True,
                    "preview_generation_error": None
                }
            else:
                return {
                    "preview_filename": None,
                    "preview_path": None,
                    "preview_generated": False,
                    "preview_generation_error": "All preview generation methods failed"
                }
                
        except Exception as e:
            logger.error(f"Error generating preview for {original_filename}: {e}")
            return {
                "preview_filename": None,
                "preview_path": None,
                "preview_generated": False,
                "preview_generation_error": str(e)
            }
    
    async def _generate_with_trimesh(self, model_path: Path, preview_path: Path) -> bool:
        """Generate preview using trimesh"""
        try:
            import trimesh
            import numpy as np
            
            # Load mesh
            mesh = trimesh.load(str(model_path))
            
            # Create scene
            scene = trimesh.Scene([mesh])
            
            # Set up camera
            scene.set_camera(angles=(0, 0, 0), distance=2.0)
            
            # Render scene to image
            png = scene.save_image(resolution=self.preview_size)
            
            if png is not None:
                # Save image
                with open(preview_path, 'wb') as f:
                    f.write(png)
                return True
            
        except ImportError:
            logger.warning("trimesh not available for preview generation")
        except Exception as e:
            logger.warning(f"Trimesh preview generation error: {e}")
        
        return False
    
    async def _generate_with_pyvista(self, model_path: Path, preview_path: Path) -> bool:
        """Generate preview using pyvista"""
        try:
            import pyvista as pv
            import numpy as np
            
            # Load mesh
            mesh = pv.read(str(model_path))
            
            # Create plotter
            plotter = pv.Plotter(off_screen=True, window_size=self.preview_size)
            plotter.add_mesh(mesh, show_edges=True, edge_color='black', line_width=0.5)
            
            # Set up camera
            plotter.camera_position = 'iso'
            plotter.camera.zoom(1.2)
            
            # Render and save
            plotter.screenshot(str(preview_path))
            plotter.close()
            
            return preview_path.exists()
            
        except ImportError:
            logger.warning("pyvista not available for preview generation")
        except Exception as e:
            logger.warning(f"Pyvista preview generation error: {e}")
        
        return False
    
    async def _generate_with_step_reader(self, model_path: Path, preview_path: Path) -> bool:
        """Generate preview using CadQuery for STEP files (Approach B: STEP → STL → Pyvista)"""
        try:
            import cadquery as cq
            from cadquery import importers, exporters
            import pyvista as pv
            import tempfile
            import os
            
            # Load STEP file with CadQuery
            model = importers.importStep(str(model_path))
            
            # Convert to STL via temporary file
            with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as temp_stl:
                temp_stl_path = temp_stl.name
            
            try:
                # Export to STL
                exporters.export(model, temp_stl_path, exportType=exporters.ExportTypes.STL)
                
                # Check if STL was created successfully
                if not os.path.exists(temp_stl_path) or os.path.getsize(temp_stl_path) == 0:
                    logger.warning(f"CadQuery STL export resulted in empty file for: {model_path}")
                    return False
                
                # Use pyvista to generate preview from STL
                mesh = pv.read(temp_stl_path)
                
                # Check if mesh has geometry
                if mesh.n_points == 0:
                    logger.warning(f"Exported STL has no geometry for: {model_path}")
                    return False
                
                # Create plotter for headless rendering
                plotter = pv.Plotter(off_screen=True, window_size=self.preview_size)
                plotter.add_mesh(mesh, show_edges=True, edge_color='black', line_width=0.5)
                
                # Set up camera
                plotter.camera_position = 'iso'
                plotter.camera.zoom(1.2)
                
                # Render and save
                plotter.screenshot(str(preview_path))
                plotter.close()
                
                return preview_path.exists()
                
            finally:
                # Clean up temporary STL file
                if os.path.exists(temp_stl_path):
                    os.unlink(temp_stl_path)
            
        except ImportError:
            logger.warning("CadQuery not available for STEP preview generation")
        except Exception as e:
            logger.warning(f"CadQuery preview generation error: {e}")
        
        return False
    
    async def _generate_step_placeholder(self, preview_path: Path) -> bool:
        """Generate a placeholder image for STEP files when conversion fails"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import os
            
            # Create a simple placeholder image
            img = Image.new('RGB', self.preview_size, color='lightgray')
            draw = ImageDraw.Draw(img)
            
            # Try to use a default font, fallback to basic if not available
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except (OSError, IOError):
                font = ImageFont.load_default()
            
            # Add text
            text = "STEP File\n(Preview not available)"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (self.preview_size[0] - text_width) // 2
            y = (self.preview_size[1] - text_height) // 2
            
            draw.text((x, y), text, fill='black', font=font)
            
            # Save the placeholder
            img.save(str(preview_path), 'PNG')
            return True
            
        except Exception as e:
            logger.warning(f"Failed to generate STEP placeholder: {e}")
            return False
    
    async def _generate_placeholder_preview(self, preview_path: Path, original_filename: str) -> bool:
        """Generate a placeholder preview image"""
        try:
            from backend.utils.helpers import generate_placeholder_preview
            
            # Generate placeholder image
            placeholder_data = generate_placeholder_preview(original_filename)
            
            # Save placeholder
            with open(preview_path, 'wb') as f:
                f.write(placeholder_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating placeholder preview: {e}")
            return False
    
    def get_preview_path(self, preview_filename: str) -> Optional[Path]:
        """Get full path to preview image"""
        if not preview_filename:
            return None
        preview_path = self.preview_dir / preview_filename
        return preview_path if preview_path.exists() else None


# Global instance
preview_generator = PreviewGenerator()
