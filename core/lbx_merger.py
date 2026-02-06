#!/usr/bin/env python3
"""
Brother P‑Touch LBX Label File Merger – visual‑spacing aware

Only the ZIP‑based (new) LBX format is supported.

Usage: $ python .\lbx_merger.py -o merged_labels.lbx -s 5 2456.lbx 3006.lbx 3007.lbx
"""

import os
import sys
import zipfile
import tempfile
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import xml.etree.ElementTree as ET

# Conversion constants
# 1 inch = 25.4 mm, 1 inch = 72 points
# Therefore: 1 point = 25.4/72 mm, and 1 mm = 72/25.4 points
MM_TO_PT = 72.0 / 25.4  # Convert millimeters to points
PT_TO_MM = 25.4 / 72.0  # Convert points to millimeters


# ---------------------------------------------------------------------------


class LbxMerger:
    """
    Merges multiple Brother P-Touch LBX label files into a single continuous label.
    
    The merger extracts each label's content (images and text), calculates their
    visual widths, and arranges them horizontally with specified spacing.
    """
    
    def __init__(self, max_length_mm: int = 300, spacing_mm: float = 3):
        """
        Initialize the merger.
        
        Args:
            max_length_mm: Maximum label length in millimeters
            spacing_mm: Spacing between labels in millimeters
        """
        self.max_length_mm = max_length_mm
        self.spacing_mm = spacing_mm
        self.spacing_pt = spacing_mm * MM_TO_PT

        # XML namespace shortcuts
        self.pt_ns = "http://schemas.brother.info/ptouch/2007/lbx/main"
        self.style_ns = "http://schemas.brother.info/ptouch/2007/lbx/style"
        self.image_ns = "http://schemas.brother.info/ptouch/2007/lbx/image"
        self.text_ns = "http://schemas.brother.info/ptouch/2007/lbx/text"

    # -----------------------------------------------------------------------
    #  XML parsing helpers
    # -----------------------------------------------------------------------

    def parse_label_xml(self, xml: str) -> ET.Element:
        """Parse XML string into an ElementTree Element."""
        return ET.fromstring(xml)

    def get_label_objects(self, root: ET.Element) -> List[ET.Element]:
        """Extract all objects from a label XML root element."""
        objects = root.find(f".//{{{self.pt_ns}}}objects")
        return list(objects) if objects is not None else []

    def get_paper_element(self, root: ET.Element) -> Optional[ET.Element]:
        """Extract the paper element from a label XML root element."""
        return root.find(f".//{{{self.style_ns}}}paper")

    def shift_object_positions(
        self, obj: ET.Element, x_offset: float, y_offset: float = 0.0
    ):
        """
        Shift an object's position by the specified offsets.
        
        Updates both objectStyle (x, y) and image orgPos (x, y) if present.
        """
        # Shift objectStyle position
        os_elem = obj.find(f".//{{{self.pt_ns}}}objectStyle")
        if os_elem is not None:
            x = float(os_elem.get("x", "0").replace("pt", ""))
            y = float(os_elem.get("y", "0").replace("pt", ""))
            os_elem.set("x", f"{x + x_offset}pt")
            os_elem.set("y", f"{y + y_offset}pt")

        # Shift image orgPos if present
        org_elem = obj.find(f".//{{{self.image_ns}}}orgPos")
        if org_elem is not None:
            x = float(org_elem.get("x", "0").replace("pt", ""))
            y = float(org_elem.get("y", "0").replace("pt", ""))
            org_elem.set("x", f"{x + x_offset}pt")
            org_elem.set("y", f"{y + y_offset}pt")

    # -----------------------------------------------------------------------
    #  Text width calculation
    # -----------------------------------------------------------------------

    def get_text_visual_width(self, text_elem: ET.Element) -> float:
        """
        Calculate the visual width (in points) of a text element.
        
        Uses Pillow to render the text and measure its actual width.
        Falls back to the XML width attribute if Pillow is unavailable.
        
        Args:
            text_elem: XML element representing a text object
            
        Returns:
            Visual width in points
        """
        NS = {
            "pt": self.pt_ns,
            "text": self.text_ns,
        }

        # Extract actual text string from <pt:data>
        text_data = text_elem.find("pt:data", NS)
        if text_data is None or text_data.text is None:
            print("Warning: no data inside text element", file=sys.stderr)
            return 0.0
        text_str = text_data.text

        # Try Pillow first for accurate measurement
        try:
            from PIL import ImageFont

            # Extract font name and size from XML
            font_name = "arial"
            size_pt = 8.0

            log_font = text_elem.find("text:ptFontInfo/text:logFont", NS)
            if log_font is not None and log_font.get("name"):
                font_name = log_font.get("name") or font_name

            font_ext = text_elem.find("text:ptFontInfo/text:fontExt", NS)
            if font_ext is not None and font_ext.get("size"):
                size_attr = font_ext.get("size")
                if size_attr.endswith("pt"):
                    size_pt = float(size_attr[:-2])
                else:
                    size_pt = float(size_attr)

            # Load the font (fallback to default if not found)
            try:
                font = ImageFont.truetype(f"{font_name}.ttf", int(round(size_pt)))
            except Exception:
                font = ImageFont.load_default()

            # Measure text width (support both Pillow 9.x and 10+)
            try:
                width, _ = font.getsize(text_str)
            except AttributeError:
                bbox = font.getbbox(text_str)
                width = bbox[2] - bbox[0]

            # Convert pixels to points (assuming 96 DPI: 1pt = 96/72 px)
            return float(width) * 72.0 / 96.0

        except Exception as e:
            # Pillow missing or failed – fallback to XML width
            print(f"Warning: using fallback width calculation, Pillow failed: {e}", file=sys.stderr)
            obj_style = text_elem.find("pt:objectStyle", NS)
            if obj_style is None:
                return 0.0
            width_attr = obj_style.get("width", "0").replace("pt", "")
            try:
                return float(width_attr)
            except ValueError:
                return 0.0

    # -----------------------------------------------------------------------
    #  Label bounding box calculation
    # -----------------------------------------------------------------------

    def calculate_label_bounds(
        self, objects: List[ET.Element], resize_text: bool = False
    ) -> Tuple[float, float]:
        """
        Calculate the bounding box (min_x, max_x) of a label's objects.
        
        For text objects, uses visual width. For other objects, uses declared width.
        Optionally resizes all text objects to match the maximum text width.
        
        Args:
            objects: List of XML elements representing label objects
            resize_text: If True, resize all text objects to max_text_width + 1pt
            
        Returns:
            Tuple of (min_x, max_x) in points
        """
        if not objects:
            return 0.0, 0.0

        min_x = float("inf")
        max_x = 0.0

        # Step 1: Find the maximum visual width of all text objects
        max_text_width = 0.0
        for obj in objects:
            if obj.tag.endswith("text"):
                vw = self.get_text_visual_width(obj)
                if vw > max_text_width:
                    max_text_width = vw

        # Step 2: Calculate bounds and optionally resize text objects
        for obj in objects:
            os_elem = obj.find(f".//{{{self.pt_ns}}}objectStyle")
            if os_elem is None:
                continue

            # Get object's x position
            try:
                x = float(os_elem.get("x", "0").replace("pt", ""))
            except ValueError:
                x = 0.0

            # Calculate object width
            if obj.tag.endswith("text"):
                # Use visual width for text when calculating bounds
                # But when resizing, we'll set it to visual width (no extra padding)
                width = max_text_width
                if resize_text:
                    # Resize text object to match visual width exactly (no extra padding)
                    os_elem.set("width", f"{max_text_width:.3f}pt")
            else:
                # For images and other objects, use declared width
                try:
                    width = float(os_elem.get("width", "0").replace("pt", ""))
                except ValueError:
                    width = 0.0

            # Update bounds
            # For text objects, we use visual width for bounds calculation
            # (the width we set in XML matches visual width, so this is consistent)
            end_x = x + width
            if end_x > max_x:
                max_x = end_x
            if x < min_x:
                min_x = x

        # Handle case where no objects were found
        if min_x == float("inf"):
            min_x = 0.0

        return min_x, max_x

    def get_label_content_width_pt(self, label_xml: str) -> float:
        """
        Calculate the visual width (in points) of a label's content.
        
        This is the distance from the leftmost to the rightmost object,
        using visual widths for text and declared widths for other objects.
        
        Args:
            label_xml: XML string of the label
            
        Returns:
            Content width in points
        """
        root = self.parse_label_xml(label_xml)
        objects = self.get_label_objects(root)
        min_x, max_x = self.calculate_label_bounds(objects, resize_text=False)
        return max_x - min_x

    def get_label_content_width_mm(self, label_xml: str) -> float:
        """Convenience wrapper – returns width in millimeters."""
        return self.get_label_content_width_pt(label_xml) * PT_TO_MM

    # -----------------------------------------------------------------------
    #  Main merge logic
    # -----------------------------------------------------------------------

    def create_merged_label_xml(self, label_contents: List[Dict]) -> str:
        """
        Merge the XML of several labels into a single continuous label.
        
        Algorithm:
        1. Use the first label as the base template
        2. Preserve the height from the first label
        3. For each label, calculate its bounding box
        4. Position labels horizontally with spacing between them
        5. Update the paper width to fit all merged content
        
        Args:
            label_contents: List of dicts with 'xml_files' and 'resources' keys
            
        Returns:
            Merged label XML as string
        """
        if not label_contents:
            return ""

        # --------------------------------------------------------------------
        #  1. Load the base label (first one) – this will be the output
        # --------------------------------------------------------------------
        base_label_xml = None
        for xml_file, content in label_contents[0]["xml_files"].items():
            if "label" in xml_file.lower():
                base_label_xml = content
                break
        if not base_label_xml:
            return ""

        base_root = self.parse_label_xml(base_label_xml)
        if base_root is None:
            return ""

        base_objects = base_root.find(f".//{{{self.pt_ns}}}objects")
        if base_objects is None:
            return ""

        # Extract and preserve height from the first label
        base_paper = self.get_paper_element(base_root)
        preserved_height = None
        if base_paper is not None and base_paper.get("height"):
            preserved_height = base_paper.get("height")
            print(f"Preserving label height: {preserved_height}")

        # --------------------------------------------------------------------
        #  2. Process first label: calculate bounds and resize text
        # --------------------------------------------------------------------
        first_objects = self.get_label_objects(base_root)
        if not first_objects:
            return ""

        first_min_x, first_max_x = self.calculate_label_bounds(
            first_objects, resize_text=True
        )
        # Account for 6mm offset - text box extends beyond calculated max_x
        offset_6mm_pt = 6.0 * MM_TO_PT
        current_x = first_max_x - offset_6mm_pt + self.spacing_pt

        # --------------------------------------------------------------------
        #  3. Merge subsequent labels
        # --------------------------------------------------------------------
        for i, label_content in enumerate(label_contents[1:], start=1):
            # Locate the XML file that contains the label
            label_xml = None
            for xml_file, content in label_content["xml_files"].items():
                if "label" in xml_file.lower():
                    label_xml = content
                    break
            if not label_xml:
                continue

            label_root = self.parse_label_xml(label_xml)
            if label_root is None:
                continue

            objects = self.get_label_objects(label_root)
            if not objects:
                continue

            # Calculate bounding box and resize text objects
            min_x, max_x = self.calculate_label_bounds(objects, resize_text=True)
            label_width = max_x - min_x

            # Calculate shift: move label so its leftmost point starts at current_x
            shift = current_x - min_x

            # Shift and add all objects to the base label
            for obj in objects:
                new_obj = ET.fromstring(ET.tostring(obj))
                self.shift_object_positions(new_obj, shift)
                base_objects.append(new_obj)

            # Update current_x for the next label
            # After shifting, the rightmost point is at: max_x + shift
            # Account for 6mm offset - text box extends beyond calculated max_x
            # So subtract 6mm from max_x when calculating where next label should start
            offset_6mm_pt = 6.0 * MM_TO_PT
            current_x = (max_x - offset_6mm_pt) + shift + self.spacing_pt

        # --------------------------------------------------------------------
        #  4. Update paper dimensions
        # --------------------------------------------------------------------
        if base_paper is not None:
            # Set width to fit all merged content (subtract last spacing)
            final_width = current_x - self.spacing_pt
            
            # Calculate height: use the maximum height from all labels
            # Check all labels to find the maximum height value
            max_height_pt = None
            if preserved_height:
                try:
                    max_height_pt = float(preserved_height.replace("pt", ""))
                except (ValueError, AttributeError):
                    max_height_pt = None
            
            # Check other labels for height
            for label_content in label_contents[1:]:
                for xml_file, content in label_content["xml_files"].items():
                    if "label" in xml_file.lower():
                        label_root = self.parse_label_xml(content)
                        paper_elem = self.get_paper_element(label_root)
                        if paper_elem is not None and paper_elem.get("height"):
                            try:
                                h = float(paper_elem.get("height").replace("pt", ""))
                                if max_height_pt is None or h > max_height_pt:
                                    max_height_pt = h
                            except (ValueError, AttributeError):
                                pass
                        break
            
            base_paper.set("width", f"{final_width:.3f}pt")
            
            # Set height: The example file uses 2834.4pt for 4 labels (708.6pt per label)
            # Input files use 850pt for 12mm labels
            # Since the editor is opening with PT-P710BT configuration, we should use
            # the same height calculation as the example: preserve original height
            # (The height doubling might be a display issue in the editor, not our code)
            height_to_set = preserved_height if preserved_height else (f"{max_height_pt:.1f}pt" if max_height_pt is not None else None)
            
            # Also ensure we use the same printer configuration as the example
            # This might affect how height is interpreted
            base_paper.set("printerID", "30256")
            base_paper.set("printerName", "Brother PT-P710BT")
            if height_to_set:
                base_paper.set("height", height_to_set)
                print(f"Set paper width: {final_width:.3f}pt, height: {height_to_set}")

        return ET.tostring(base_root, encoding="unicode")

    # -----------------------------------------------------------------------
    #  File I/O and ZIP handling
    # -----------------------------------------------------------------------

    def extract_label_content_zip(self, filepath: Path) -> Dict:
        """
        Extract the XML files and binary resources from a ZIP‑based LBX.
        
        Args:
            filepath: Path to the LBX file
            
        Returns:
            Dict with keys 'xml_files' and 'resources'
        """
        label_data: Dict[str, Dict] = {"xml_files": {}, "resources": {}}
        try:
            with zipfile.ZipFile(filepath, "r") as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    data = z.read(info.filename)
                    if info.filename.lower().endswith(".xml"):
                        label_data["xml_files"][info.filename] = data.decode()
                    else:
                        label_data["resources"][info.filename] = data
            return label_data
        except Exception as e:
            print(f"Error: Failed extracting label content from {filepath}: {e}", file=sys.stderr)
            return label_data

    def merge_properties_xml(self, label_contents: List[Dict]) -> str:
        """
        Extract properties XML from the first label.
        
        Args:
            label_contents: List of label content dicts
            
        Returns:
            Properties XML as string, or empty string if not found
        """
        if not label_contents:
            return ""
        for xml_file, content in label_contents[0]["xml_files"].items():
            if "prop" in xml_file.lower():
                return content
        return ""

    def merge_zip_based_labels(
        self, label_contents: List[Dict], output_path: Path
    ) -> bool:
        """
        Merge ZIP-based labels and write the result to a new LBX file.
        
        Args:
            label_contents: List of label content dicts
            output_path: Path for the output LBX file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Generate merged label XML
                merged_label_xml = self.create_merged_label_xml(label_contents)
                if not merged_label_xml:
                    print("Error: Failed to create merged label XML", file=sys.stderr)
                    return False

                # Write the merged XML
                label_xml_path = os.path.join(tmpdir, "label.xml")
                with open(label_xml_path, "w", encoding="utf-8") as f:
                    f.write(merged_label_xml)

                # Write merged properties if any
                merged_props_xml = self.merge_properties_xml(label_contents)
                if merged_props_xml:
                    props_xml_path = os.path.join(tmpdir, "prop.xml")
                    with open(props_xml_path, "w", encoding="utf-8") as f:
                        f.write(merged_props_xml)

                # Collect all unique resources (images, etc.)
                all_resources = {}
                for content in label_contents:
                    for rel_path, data in content.get("resources", {}).items():
                        if rel_path not in all_resources:
                            all_resources[rel_path] = data

                # Write resources to temporary directory
                for rel_path, data in all_resources.items():
                    full_path = os.path.join(tmpdir, rel_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "wb") as f:
                        f.write(data)

                # Create the final LBX (ZIP) file
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
                    for root, dirs, files in os.walk(tmpdir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arc_path = os.path.relpath(full_path, tmpdir)
                            z.write(full_path, arc_path)

                return True
        except Exception as e:
            print(f"Error merging ZIP-based labels: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False

    # -----------------------------------------------------------------------
    #  Main merge entry point
    # -----------------------------------------------------------------------

    def merge_labels(self, input_files: List[Path], output_file: Path) -> bool:
        """
        Merge multiple LBX label files into a single output file.
        
        Args:
            input_files: List of input LBX file paths
            output_file: Path for the output LBX file
            
        Returns:
            True if successful, False otherwise
        """
        if not input_files:
            print("Error: No input files provided", file=sys.stderr)
            return False

        # Extract content from all input files
        label_contents = []
        for f in input_files:
            content = self.extract_label_content_zip(f)
            if content and content.get("xml_files"):
                label_contents.append(content)
            else:
                print(f"Warning: Could not extract content from {f}", file=sys.stderr)

        if not label_contents:
            print("Error: No valid label content extracted", file=sys.stderr)
            return False

        # Filter labels that fit within max length
        max_length_pt = self.max_length_mm * MM_TO_PT
        selected_contents: List[Dict] = []
        current_width_pt = 0.0
        skipped: List[Path] = []

        for idx, content in enumerate(label_contents):
            # Find the label XML file
            label_xml = next(
                (
                    c
                    for f, c in content["xml_files"].items()
                    if f.lower() == "label.xml"
                ),
                None,
            )
            if not label_xml:
                continue

            # Calculate width of this label
            label_width_pt = self.get_label_content_width_pt(label_xml)

            # Add spacing only if this is not the first label
            label_width_with_spacing = label_width_pt
            if selected_contents:
                label_width_with_spacing += self.spacing_pt

            # Check if this label would exceed the limit
            if current_width_pt + label_width_with_spacing > max_length_pt:
                skipped.append(input_files[idx])
                print(
                    f"Skipping {input_files[idx]} – "
                    f"would exceed max length {self.max_length_mm} mm."
                )
                continue

            # Accept this label
            current_width_pt += label_width_with_spacing
            selected_contents.append(content)

        if not selected_contents:
            print("Error: No labels fit within the requested maximum length.", file=sys.stderr)
            return False

        if skipped:
            print(f"Note: {len(skipped)} label(s) were skipped due to length limit.")

        # Merge the selected labels
        return self.merge_zip_based_labels(selected_contents, output_file)


# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Merge multiple Brother P‑Touch .lbx label files into a single continuous label"
    )
    parser.add_argument(
        "input_files", nargs="+", type=Path, help="Input .lbx files to merge"
    )
    parser.add_argument(
        "-o", "--output", type=Path, required=True, help="Output .lbx file path"
    )
    parser.add_argument(
        "-m",
        "--max-length",
        type=int,
        default=300,
        help="Maximum label length in mm (default: 300)",
    )
    parser.add_argument(
        "-s",
        "--spacing",
        type=float,
        default=3,
        help="Spacing between labels in mm (default: 3)",
    )
    args = parser.parse_args()

    # Validate input files
    for f in args.input_files:
        if not f.exists():
            print(f"Error: Input file {f} does not exist", file=sys.stderr)
            sys.exit(1)
        if not str(f).lower().endswith(".lbx"):
            print(f"Warning: {f} does not have .lbx extension", file=sys.stderr)

    # Perform merge
    merger = LbxMerger(max_length_mm=args.max_length, spacing_mm=args.spacing)
    print(f"Merging {len(args.input_files)} label file(s) into a continuous label...")
    success = merger.merge_labels(args.input_files, args.output)

    if success:
        print(f"Successfully created merged continuous label: {args.output}")
        print("The merged label should now be openable in P-Touch Editor.")
        sys.exit(0)
    else:
        print("Failed to merge labels", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
