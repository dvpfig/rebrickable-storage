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
        self.cache_images_rb = self.global_cache_dir / "images_rb"
        self.cache_labels = self.global_cache_dir / "labels"
        self.cache_set_inventories = self.global_cache_dir / "set_inventories"
        self.resources_dir = self.root / "resources"
        self.user_data_dir = self.root / "user_data"

        # Use helper function to find latest mapping file
        from resources.ba_part_mappings import find_latest_mapping_file
        latest_mapping = find_latest_mapping_file(self.resources_dir)
        if latest_mapping:
            self.mapping_path = latest_mapping
        else:
            # No mapping file found - display error to user
            self.mapping_path = None
            st.error("❌ **No mapping file found!**")
            st.warning(
                "⚠️ No BA vs RB mapping file was found in the resources directory. "
                "Please create a mapping file by using the sidebar option: "
                "**'Sync latest Parts from BrickArchitect' → 'Get full list of BA parts'**"
            )
            st.info(
                "💡 The mapping file should be named in the format: "
                "`part number - BA vs RB - YYYY-MM-DD.xlsx`"
            )
            st.stop()

        self.colors_path = self.resources_dir / "colors.csv"

        for d in [self.global_cache_dir, self.cache_images, self.cache_images_rb, self.cache_labels, self.cache_set_inventories, self.resources_dir, self.user_data_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_user_uploaded_images_dir(self, username: str) -> Path:
        """Get the user-specific uploaded images directory."""
        user_images_dir = self.user_data_dir / username / "images_uploaded"
        user_images_dir.mkdir(parents=True, exist_ok=True)
        return user_images_dir
    
    def get_user_sets_dir(self, username: str) -> Path:
        """Get the user-specific sets directory."""
        sets_dir = self.user_data_dir / username / "sets"
        sets_dir.mkdir(parents=True, exist_ok=True)
        return sets_dir
    
    def get_user_collection_parts_dir(self, username: str) -> Path:
        """Get the user-specific collection parts directory."""
        collection_parts_dir = self.user_data_dir / username / "collection_parts"
        collection_parts_dir.mkdir(parents=True, exist_ok=True)
        return collection_parts_dir

    def get_user_collection_sets_dir(self, username: str) -> Path:
        """Get the user-specific collection sets directory."""
        collection_sets_dir = self.user_data_dir / username / "collection_sets"
        collection_sets_dir.mkdir(parents=True, exist_ok=True)
        return collection_sets_dir

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