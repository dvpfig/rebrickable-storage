# core/paths.py
import streamlit as st
from pathlib import Path
import os

class Paths:
    """
    Centralized path management for the application.
    
    Handles all file system paths including cache directories, user data,
    and resource files. Ensures cross-platform compatibility.
    """
    def __init__(self):
        """Initialize all application paths and create necessary directories."""
        try:
            # Go up 2 levels: core/infrastructure/paths.py -> core/ -> root/
            self.root = Path(__file__).resolve().parents[2]
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
        from core.external.ba_part_mappings import find_latest_mapping_file
        latest_mapping = find_latest_mapping_file(self.resources_dir)
        # mapping_path may be None when no mapping file exists yet
        self.mapping_path = latest_mapping

        self.colors_path = self.resources_dir / "colors.csv"

        # Auto-download colors.csv from Rebrickable if not present
        if not self.colors_path.exists():
            from core.data.colors import ensure_colors_csv
            if not ensure_colors_csv(self.colors_path):
                st.warning(
                    "⚠️ Could not download colors.csv from Rebrickable. "
                    "Color information will be unavailable until the file is downloaded. "
                    "Use the sidebar option in 'My Collection - Parts' to retry."
                )

        for d in [self.global_cache_dir, self.cache_images, self.cache_images_rb, self.cache_labels, self.cache_set_inventories, self.resources_dir, self.user_data_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_user_uploaded_images_dir(self, username: str) -> Path:
        """
        Get the user-specific uploaded images directory.
        
        Args:
            username: Username for the directory
            
        Returns:
            Path: Path to user's uploaded images directory
        """
        user_images_dir = self.user_data_dir / username / "images_uploaded"
        user_images_dir.mkdir(parents=True, exist_ok=True)
        return user_images_dir
    
    
    def get_user_collection_parts_dir(self, username: str) -> Path:
        """
        Get the user-specific collection parts directory.
        
        Args:
            username: Username for the directory
            
        Returns:
            Path: Path to user's collection parts directory
        """
        collection_parts_dir = self.user_data_dir / username / "collection_parts"
        collection_parts_dir.mkdir(parents=True, exist_ok=True)
        return collection_parts_dir

    def get_user_collection_sets_dir(self, username: str) -> Path:
        """
        Get the user-specific collection sets directory.
        
        Args:
            username: Username for the directory
            
        Returns:
            Path: Path to user's collection sets directory
        """
        collection_sets_dir = self.user_data_dir / username / "collection_sets"
        collection_sets_dir.mkdir(parents=True, exist_ok=True)
        return collection_sets_dir

    @property
    def has_mapping(self) -> bool:
        """Check if a valid mapping file is available."""
        return self.mapping_path is not None


def show_missing_mapping_error(stop: bool = True):
    """
    Display a user-friendly error when no mapping file is found,
    with a navigation link to the page where it can be created.
    
    Args:
        stop: If True, call st.stop() after displaying the error.
    """
    st.error("❌ **No mapping file found!**")
    st.warning(
        "⚠️ No BA vs RB mapping file was found in the resources directory. "
        "Please create one by going to **My Collection - Parts** and using "
        "**'🔄 Sync latest Parts from BrickArchitect' → 'Get full list of BA parts'**."
    )
    st.page_link(
        "pages/2_My_Collection_Parts.py",
        label="📦 Go to My Collection - Parts",
        icon="➡️",
    )
    st.info(
        "💡 The mapping file should be named in the format: "
        "`base_part_mapping_YYYY-MM-DD.xlsx`"
    )
    if stop:
        st.stop()

def init_paths() -> Paths:
    """
    Initialize and return the Paths object.
    Caches the instance in session state to avoid redundant directory scanning
    and mkdir calls across reruns and pages.
    
    Returns:
        Paths: Configured Paths instance
    """
    try:
        # Cache in session state to avoid re-creating on every rerun
        if "_paths_instance" not in st.session_state:
            st.session_state["_paths_instance"] = Paths()
        return st.session_state["_paths_instance"]
    except Exception:
        # Fallback if session state is unavailable (e.g., during testing)
        return Paths()


def save_uploadedfiles(uploadedfiles_list, user_collection_dir: Path):
    """
    Save uploaded files to user's collection directory.
    
    Args:
        uploadedfiles_list: List of Streamlit UploadedFile objects
        user_collection_dir: Path to user's collection directory
        
    Returns:
        Streamlit success message or None if no files
    """
    if uploadedfiles_list:
        for uploadedfile in uploadedfiles_list:
            with open(os.path.join(user_collection_dir,uploadedfile.name),"wb") as f:
                f.write(uploadedfile.getbuffer())
        return st.success("Saved files to user collection!")
    else:
        return
        
def manage_default_collection(user_collection_dir: Path):
    """
    Display UI for managing (deleting) collection CSV files.
    
    Args:
        user_collection_dir: Path to user's collection directory
        
    Returns:
        None
    """
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