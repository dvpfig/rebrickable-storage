# core/paths.py
import streamlit as st
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
        self.user_data_dir = self.root / "user_data"

        self.mapping_path = self.resources_dir / "part number - BA vs RB - 2025-11-11.xlsx"
        self.colors_path = self.resources_dir / "colors.csv"

        for d in [self.global_cache_dir, self.cache_images, self.resources_dir, self.default_collection_dir, self.user_data_dir]:
            d.mkdir(parents=True, exist_ok=True)

def init_paths() -> Paths:
    return Paths()


def save_uploadedfiles(uploadedfiles_list, user_collection_dir: Path):
    if uploadedfiles_list:
        for uploadedfile in uploadedfiles_list:
            with open(os.path.join(user_collection_dir,uploadedfile.name),"wb") as f:
                f.write(uploadedfile.getbuffer())
        return st.success("Saved files to user collection!")
    else:
        return
        
def manage_default_collection(user_collection_dir: Path):
    default_collection_files = sorted(user_collection_dir.glob("*.csv"))
    if default_collection_files:
        mark_for_delete = False
        if st.button("Delete selected files"):
            mark_for_delete = True
        
        for csv_file in default_collection_files:
            include = st.checkbox(f"{csv_file.name}", value=False, key=f"del_{csv_file.name}")
            if include & mark_for_delete:
                os.remove(csv_file)
            
    return