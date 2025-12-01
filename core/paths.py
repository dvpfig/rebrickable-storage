# core/paths.py
from pathlib import Path
import os

class Paths:
    def __init__(self):
        try:
            self.root = Path(__file__).resolve().parents[1]
        except NameError:
            self.root = Path(os.getcwd()).resolve()

        self.global_cache_dir = self.root / "cache"
        self.cache_images = self.global_cache_dir / "images"
        self.resources_dir = self.root / "resources"
        self.default_collection_dir = self.root / "collection"

        self.mapping_path = self.resources_dir / "part number - BA vs RB - 2025-11-11.xlsx"
        self.colors_path = self.resources_dir / "colors.csv"

        for d in [self.global_cache_dir, self.cache_images, self.resources_dir, self.default_collection_dir]:
            d.mkdir(parents=True, exist_ok=True)

def init_paths() -> Paths:
    return Paths()
