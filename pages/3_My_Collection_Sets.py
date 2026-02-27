"""
My Collection - Sets page for managing LEGO set collections.

This page allows users to:
- Upload CSV files containing their LEGO sets
- Manually enter set numbers
- Store and validate Rebrickable API keys
- Retrieve set inventories from Rebrickable API
- View and manage their set collection
"""

import streamlit as st
from pathlib import Path

from core.infrastructure.paths import init_paths
from core.data.sets import SetsManager
from core.auth.api_keys import load_api_key, save_api_key
from core.external.rebrickable_api import RebrickableAPI, APIError

# Page configuration
st.title("📦 My Collection - Sets")
st.sidebar.header("📦 My Collection - Sets")

# Check authentication early
if not st.session_state.get("authentication_status"):
    st.warning("⚠️ Please login on the first page to access this feature.")
    if st.button("🔐 Go to Login Page"):
        st.switch_page("pages/1_Rebrickable_Storage.py")
    st.stop()

# Get paths and user info early for sidebar
paths = init_paths()
username = st.session_state.get("username")
user_data_dir = paths.user_data_dir / username

def render_csv_upload_section(sets_manager: SetsManager) -> None:
    """
    Render CSV file upload interface.
    
    Args:
        sets_manager: SetsManager instance for handling CSV operations
    """
    st.markdown("### 📤 Upload Sets CSV")
    st.markdown("""
    Upload CSV files containing your LEGO sets. Expected format (Rebrickable CSV export):
    - **Set number**: LEGO set number (e.g., "31147-1")
    - **Quantity**: Number of this set owned
    - **Includes spares**: Whether to include spare parts
    - **Inventory ver**: Rebrickable inventory version
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload CSV file(s) with Collection of Sets",
        type=['csv'],
        key="sets_csv_uploader",
        help="Upload a CSV file with your LEGO sets collection"
    )
    
    if uploaded_file is not None:
        # Show file details
        st.info(f"📄 File: **{uploaded_file.name}** ({uploaded_file.size} bytes)")
        
        # Add a button to process the file
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📥 Import Sets", key="import_csv_button", type="primary"):
                try:
                    # Parse and validate CSV
                    with st.spinner("Parsing CSV file..."):
                        new_sets = sets_manager.load_sets_from_csv(
                            uploaded_file, 
                            source_name=uploaded_file.name
                        )
                    
                    # Load existing sets
                    existing_sets = sets_manager.load_sets_metadata()
                    
                    # Check for duplicates
                    existing_set_numbers = {s["set_number"] for s in existing_sets}
                    duplicates = [s for s in new_sets if s["set_number"] in existing_set_numbers]
                    new_unique_sets = [s for s in new_sets if s["set_number"] not in existing_set_numbers]
                    
                    if duplicates:
                        st.warning(
                            f"⚠️ Skipped {len(duplicates)} duplicate set(s): "
                            f"{', '.join([s['set_number'] for s in duplicates[:5]])}"
                            f"{'...' if len(duplicates) > 5 else ''}"
                        )
                    
                    if new_unique_sets:
                        # Save uploaded CSV file to user's sets directory
                        csv_save_path = sets_manager.sets_dir / uploaded_file.name
                        with open(csv_save_path, 'wb') as f:
                            f.write(uploaded_file.getvalue())
                        
                        # Merge with existing sets and save
                        all_sets = existing_sets + new_unique_sets
                        sets_manager.save_sets_metadata(all_sets)
                        
                        # Update session state
                        sets_manager.save_to_session_state(st.session_state)
                        
                        st.success(
                            f"✅ Successfully imported **{len(new_unique_sets)}** set(s) from **{uploaded_file.name}**!"
                        )
                        st.rerun()
                    elif not duplicates:
                        st.warning("⚠️ No sets found in the CSV file.")
                    else:
                        st.info("ℹ️ All sets from this file are already in your collection.")
                        
                except ValueError as e:
                    st.error(f"❌ Invalid CSV format: {str(e)}")
                    st.markdown("""
                    **Expected CSV format:**
                    ```
                    Set number,Quantity,Includes spares,Inventory ver
                    31147-1,1,true,1
                    10497-1,2,true,1
                    ```
                    """)
                except Exception as e:
                    st.error(f"❌ Error processing CSV file: {str(e)}")


def render_manual_entry_section(sets_manager: SetsManager) -> None:
    """
    Render manual set number entry interface.
    
    Args:
        sets_manager: SetsManager instance for handling manual set entry
    """
    st.markdown("### ✏️ Add Set Manually")
    st.markdown("Enter a single set number to add it to your collection.")
    
    # Input for set number
    col1, col2 = st.columns([2, 2])
    
    with col1:
        set_number_input = st.text_input(
            "Set Number",
            placeholder="e.g., 31147-1",
            key="manual_set_number_input",
            help="Enter a LEGO set number (e.g., 31147-1)"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing to align button
        if st.button("➕ Add Set", key="add_manual_set_button", width='stretch'):
            if set_number_input and set_number_input.strip():
                try:
                    # Add the set
                    with st.spinner(f"Adding set {set_number_input.strip()}..."):
                        set_data = sets_manager.add_manual_set(set_number_input.strip())
                    
                    # Update session state
                    sets_manager.save_to_session_state(st.session_state)
                    
                    st.success(
                        f"✅ Successfully added set **{set_data['set_number']}** to your collection!"
                    )
                    st.info("💡 Remember to retrieve inventories to enable part searching.")
                    st.rerun()
                    
                except ValueError as e:
                    # Handle validation errors (empty, duplicate, etc.)
                    st.error(f"❌ {str(e)}")
                except Exception as e:
                    st.error(f"❌ Error adding set: {str(e)}")
            else:
                st.warning("⚠️ Please enter a set number")


def render_inventory_fetch_section(sets_manager: SetsManager, api_client: RebrickableAPI = None) -> None:
    """
    Render inventory retrieval interface with progress tracking.
    
    Args:
        sets_manager: SetsManager instance for handling inventory operations
        api_client: Optional configured RebrickableAPI client
    """
    st.markdown("### 🔄 Retrieve Inventories")
    st.markdown("Fetch part inventories for your sets from Rebrickable.")
    
    # Load sets from session state if available, otherwise from disk
    if st.session_state.get("sets_data_loaded", False) and st.session_state.get("sets_metadata") is not None:
        sets = st.session_state["sets_metadata"]
    else:
        sets = sets_manager.load_sets_metadata()
    
    if not sets:
        st.info("📭 No sets in your collection. Add sets above to retrieve their inventories.")
        return
    
    # Check if API key is configured
    if not api_client:
        st.warning("⚠️ Please configure your Rebrickable API key above to retrieve inventories.")
        return
    
    # Count sets that need fetching
    unfetched_sets = [s for s in sets if not s.get("inventory_fetched", False)]
    fetched_sets = [s for s in sets if s.get("inventory_fetched", False)]
    
    # Display status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sets", len(sets))
    with col2:
        st.metric("Fetched", len(fetched_sets))
    with col3:
        st.metric("Pending", len(unfetched_sets))
    
    # Button to retrieve inventories
    if unfetched_sets:
        st.markdown(f"**{len(unfetched_sets)}** set(s) need inventory data.")
        
        if st.button("🔄 Retrieve Inventories", key="retrieve_inventories_button", type="primary"):
            # Create placeholders for progress display
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Progress callback function
            def update_progress(current, total, set_number, status):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Processing {current}/{total}: {set_number} - {status}")
            
            # Fetch inventories
            try:
                with st.spinner("Retrieving inventories..."):
                    stats = sets_manager.fetch_all_inventories(
                        api_client,
                        progress_callback=update_progress
                    )
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Display summary
                st.markdown("### 📊 Retrieval Summary")
                
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                with summary_col1:
                    st.success(f"✅ **{stats['successful']}** successful")
                with summary_col2:
                    if stats['skipped'] > 0:
                        st.info(f"⏭️ **{stats['skipped']}** skipped (cached)")
                with summary_col3:
                    if stats['failed'] > 0:
                        st.error(f"❌ **{stats['failed']}** failed")
                
                # Display errors if any
                if stats['errors']:
                    with st.expander("⚠️ View Errors", expanded=False):
                        for error in stats['errors']:
                            st.text(f"• {error}")
                
                # Show success message
                if stats['successful'] > 0:
                    # Update session state with new inventories
                    sets_manager.save_to_session_state(st.session_state)
                    
                    st.success(
                        f"🎉 Successfully retrieved inventories for **{stats['successful']}** set(s)! "
                        "You can now search for parts in these sets."
                    )
                
                # Rerun to update the display
                if stats['successful'] > 0 or stats['failed'] > 0:
                    st.rerun()
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ Error during inventory retrieval: {str(e)}")
                st.markdown("""
                **Possible issues:**
                - Network connectivity problems
                - API rate limiting
                - Invalid API key
                
                Please try again in a few moments.
                """)
    else:
        st.success("✅ All sets have their inventories fetched!")
        st.info("💡 If you add new sets, return here to retrieve their inventories.")


def render_sets_display(sets_manager: SetsManager) -> None:
    """
    Render sets list grouped by source CSV.
    
    Shows set number, name, quantity, and part count for each set.
    Includes delete buttons for individual sets and source groups.
    
    Args:
        sets_manager: SetsManager instance for handling set operations
    """
    # Load sets from session state if available, otherwise from disk
    if st.session_state.get("sets_data_loaded", False) and st.session_state.get("sets_metadata") is not None:
        sets = st.session_state["sets_metadata"]
        # Group by source
        sets_by_source = {}
        for set_data in sets:
            source = set_data["source_csv"]
            if source not in sets_by_source:
                sets_by_source[source] = []
            sets_by_source[source].append(set_data)
    else:
        # Fallback to loading from disk
        sets_by_source = sets_manager.get_sets_by_source()
    
    if not sets_by_source:
        st.info("📭 No sets in your collection yet. Upload a CSV file or add sets manually above.")
        return
    
    # Display summary
    total_sets = sum(len(sets) for sets in sets_by_source.values())
    st.markdown(f"**{total_sets}** set(s) from **{len(sets_by_source)}** source(s)")
    
    # Display each source group
    for source_name, sets in sets_by_source.items():
        with st.expander(f"📁 **{source_name}** ({len(sets)} set(s))", expanded=True):
            # Add delete source group button
            col1, col2 = st.columns([3, 1])
            with col2:
                delete_group_key = f"delete_group_{source_name}"
                if st.button(
                    "🗑️ Delete Group",
                    key=delete_group_key,
                    help=f"Delete all sets from {source_name}",
                    type="secondary"
                ):
                    # Store deletion request in session state for confirmation
                    st.session_state[f"confirm_delete_group_{source_name}"] = True
                    st.rerun()
            
            # Check if confirmation is needed
            if st.session_state.get(f"confirm_delete_group_{source_name}", False):
                st.warning(f"⚠️ Are you sure you want to delete all **{len(sets)}** set(s) from **{source_name}**?")
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("✅ Yes, Delete", key=f"confirm_yes_{source_name}", type="primary"):
                        try:
                            sets_manager.delete_source_group(source_name)
                            
                            # Update session state
                            sets_manager.save_to_session_state(st.session_state)
                            
                            st.success(f"✅ Deleted all sets from **{source_name}**")
                            # Clear confirmation state
                            del st.session_state[f"confirm_delete_group_{source_name}"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting source group: {str(e)}")
                with col2:
                    if st.button("❌ Cancel", key=f"confirm_no_{source_name}"):
                        # Clear confirmation state
                        del st.session_state[f"confirm_delete_group_{source_name}"]
                        st.rerun()
                
                # Don't show the sets list while confirmation is pending
                return
            
            # Display sets in a table-like format
            for set_data in sets:
                set_number = set_data.get("set_number", "Unknown")
                set_name = set_data.get("set_name", "Unknown Set")
                quantity = set_data.get("quantity", 1)
                part_count = set_data.get("part_count", 0)
                inventory_fetched = set_data.get("inventory_fetched", False)
                
                # Create columns for set display
                col1, col2, col3, col4, col5 = st.columns([2, 3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{set_number}**")
                
                with col2:
                    st.markdown(f"{set_name}")
                
                with col3:
                    st.markdown(f"Qty: **{quantity}**")
                
                with col4:
                    if inventory_fetched and part_count > 0:
                        st.markdown(f"🧩 **{part_count}** parts")
                    elif inventory_fetched:
                        st.markdown("🧩 Fetched")
                    else:
                        st.markdown("⏳ Pending")
                
                with col5:
                    delete_key = f"delete_{set_number}_{source_name}"
                    if st.button("🗑️", key=delete_key, help=f"Delete {set_number}"):
                        # Store deletion request in session state for confirmation
                        st.session_state[f"confirm_delete_{set_number}"] = True
                        st.rerun()
                
                # Check if confirmation is needed for this specific set
                if st.session_state.get(f"confirm_delete_{set_number}", False):
                    st.warning(f"⚠️ Delete set **{set_number} - {set_name}**?")
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("✅ Yes", key=f"confirm_yes_set_{set_number}", type="primary"):
                            try:
                                sets_manager.delete_set(set_number)
                                
                                # Update session state
                                sets_manager.save_to_session_state(st.session_state)
                                
                                st.success(f"✅ Deleted set **{set_number}**")
                                # Clear confirmation state
                                del st.session_state[f"confirm_delete_{set_number}"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error deleting set: {str(e)}")
                    with col2:
                        if st.button("❌ No", key=f"confirm_no_set_{set_number}"):
                            # Clear confirmation state
                            del st.session_state[f"confirm_delete_{set_number}"]
                            st.rerun()
                
                # Add a subtle divider between sets
                st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)


def render_api_key_section(user_data_dir: Path, current_api_key: str = None, in_sidebar: bool = False) -> str:
    """
    Render API key input and validation section.
    
    Args:
        user_data_dir: Path to user's data directory
        current_api_key: Currently saved API key (if any)
        in_sidebar: Whether this is being rendered in the sidebar
        
    Returns:
        Updated API key if saved, otherwise current_api_key
    """
    if not in_sidebar:
        st.markdown("### 🔑 Rebrickable API Key")
    st.markdown("""
    To retrieve set inventories, you need a Rebrickable API key. 
    Get your free API key at [rebrickable.com/api](https://rebrickable.com/api/).
    """)
    
    # Show current status
    if current_api_key:
        st.success("✅ API key is configured")
        
        # Option to update the key
        with st.expander("🔄 Update API Key"):
            new_key = st.text_input(
                "Enter new API key",
                type="password",
                key="new_api_key_input",
                help="Your Rebrickable API key will be validated before saving"
            )
            
            if st.button("💾 Save New Key", key="save_new_api_key", type="primary"):
                if new_key and new_key.strip():
                    # Validate the new key
                    with st.spinner("Validating API key..."):
                        try:
                            api_client = RebrickableAPI(new_key.strip())
                            if api_client.validate_key():
                                save_api_key(user_data_dir, new_key.strip())
                                st.success("✅ API key validated and saved successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid API key. Please check your key and try again.")
                        except Exception as e:
                            st.error(f"❌ Error validating API key: {str(e)}")
                else:
                    st.warning("⚠️ Please enter an API key")
    else:
        st.info("ℹ️ No API key configured. Add your API key to retrieve set inventories.")
        
        # Input for new API key
        api_key_input = st.text_input(
            "Enter your Rebrickable API key",
            type="password",
            key="api_key_input",
            help="Your Rebrickable API key will be validated before saving"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save API Key", key="save_api_key"):
                if api_key_input and api_key_input.strip():
                    # Validate the key
                    with st.spinner("Validating API key..."):
                        try:
                            api_client = RebrickableAPI(api_key_input.strip())
                            if api_client.validate_key():
                                save_api_key(user_data_dir, api_key_input.strip())
                                st.success("✅ API key validated and saved successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid API key. Please check your key and try again.")
                        except Exception as e:
                            st.error(f"❌ Error validating API key: {str(e)}")
                else:
                    st.warning("⚠️ Please enter an API key")
    
    return current_api_key


# Sidebar - API Key Management Section
with st.sidebar:
    st.markdown("---")
    with st.expander("🔑 Rebrickable API Key", expanded=False):
        api_key = load_api_key(user_data_dir)
        api_key = render_api_key_section(user_data_dir, api_key, in_sidebar=True)

# Initialize SetsManager
sets_manager = SetsManager(user_data_dir, paths.cache_set_inventories)

# Reuse the api_key already loaded above (no need to call load_api_key again)
if api_key:
    sets_manager.api_key = api_key

# Ensure sets data is loaded into session state once (avoids duplicate disk reads)
if not st.session_state.get("sets_data_loaded", False):
    sets_manager.load_into_session_state(st.session_state)

# Main page layout
st.markdown("""
This page allows you to manage your LEGO set collection. Upload CSV files or manually enter 
set numbers, then retrieve inventories from Rebrickable to enable searching for parts within your sets.
""")

st.markdown("---")

# CSV Upload and Manual Entry Sections - Side by Side
col1, col2 = st.columns(2)

with col1:
    render_csv_upload_section(sets_manager)

with col2:
    render_manual_entry_section(sets_manager)

st.markdown("---")

# Inventory Retrieval Section
# Create API client if API key is available
api_client = None
if api_key:
    try:
        api_client = RebrickableAPI(api_key)
    except Exception as e:
        st.error(f"❌ Error initializing API client: {str(e)}")

render_inventory_fetch_section(sets_manager, api_client)

st.markdown("---")

# Sets Display Section
st.markdown("### 📋 Your Sets Collection")

# Display sets grouped by source
render_sets_display(sets_manager)
