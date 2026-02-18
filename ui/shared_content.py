# ui/about_info.py
import streamlit as st


def render_about_info_content():
    """
    Render About & Info content with application information.
    This content is reused on both the landing page (for unauthenticated users)
    and the About page (for authenticated users).
    """
    
    # Welcome message
    st.markdown(""" ## 🧱 Lego Parts Collection - Storage Labels & Parts Finder 
    
    A powerful web application designed for LEGO enthusiasts to efficiently manage 
    and locate parts from their collection. Whether you're building a new set or 
    organizing your storage, this tool helps you find exactly what you need, 
    exactly where it is.
    - 🏷️ Label Generation
    - 🔍 Parts Finding
    - 🧩 Rebrickable Parts Integration
    - 🖼️ Visual Integration (Brickarchitect)
    - 💾 Progress Tracking

    Powered by [BrickArchitect Lego Parts Guide](https://brickarchitect.com/parts/) & [Rebrickable Lego Collection Lists](https://rebrickable.com/) • Made with ❤️ and Streamlit
    """)
    
    # Open source information
    st.info("""
    **🌟 Open Source Project**

    This application is open source and available on Github!

    🔗 [Github Repository](https://github.com/dvpfig/rebrickable-storage)
    """)
    
def render_app_features_content():
    """
    Render App Features content with application funtionality and features.
    This content is reused on both the landing page (for unauthenticated users)
    and the About page (for authenticated users).
    """
    
    # Main functionalities
    st.markdown("## 🎯 Two Main Functionalities")
    
    # Functionality 1: Label Generation
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🏷️ Label Generation")
    
    with col2:
        st.markdown("""
        **Organize your physical storage with printable labels**
        
        1. **Upload** your collection CSV files (from Rebrickable)
        2. **Select** which collection files to include
        3. **Generate** printable labels organized by storage location
        4. **Download** the ZIP file with labels (.lbx or image formats)
        5. **Print** and attach labels to your storage containers
        
        Perfect for maintaining an organized LEGO parts collection with clear labeling!
        """)
    
    st.markdown("---")
    
    # Functionality 2: Parts Finding
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🔍 Parts Finding")
    
    with col2:
        st.markdown("""
        **Find parts you need for new constructions**
        
        1. **Upload** wanted parts CSV (from Rebrickable set inventory)
        2. **Select** your collection files to search through
        3. **Generate** a pickup list showing parts grouped by storage location
        4. **View** part images, colors, and quantities for easy identification
        5. **Mark** parts as found while collecting them
        6. **Save** your progress and resume later
        
        Streamlines the process of gathering parts for your next build!
        """)
    
    st.markdown("---")
    
    # Key features
    st.markdown("## ✨ Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🧩 Rebrickable Parts Integration**
        - Upload exported collection from Rebrickable
        - Handles large collections (e.g. 100k parts)
        - Parses location information in collection files
        - Upload exported wanted parts from Rebrickable (e.g. MOC inventory)
        """)
    
    with col2:
        st.markdown("""
        **🖼️ Visual Integration**
        - Part images from BrickArchitect
        - Color-coded display
        - Alternative color suggestions
        - Custom image uploads
        """)
    
    with col3:
        st.markdown("""
        **💾 Progress Tracking**
        - Save and load progress
        - Session state preservation
        - Audit logging
        - Data persistence
        """)
    
    st.markdown("---")


def render_new_user_content():
    """
    Render information for new users with information about demo login (unauthenticated users).
    """

    # Getting started
    st.markdown("## 🚀 Getting Started")
    
    st.markdown("""
    **New users:** Register an account to get started with your own collection.
    
    **Demo available:** Try the app with demo credentials: username: `demo` & password: `demo123`
    """)
