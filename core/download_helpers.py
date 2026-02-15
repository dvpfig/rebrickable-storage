# core/download_helpers.py
"""
Helper functions for managing download progress and callbacks in the UI.
"""
import streamlit as st


class DownloadCallbacks:
    """
    Creates and manages callback functions for download progress tracking.
    
    This class provides a unified interface for progress, stop flag, and stats callbacks
    that can be used with various download functions (labels, images, parts, mappings).
    """
    
    def __init__(self, stop_flag_key: str, show_stats: bool = False, stats_formatter=None):
        """
        Initialize download callbacks.
        
        Args:
            stop_flag_key: Session state key for the stop flag (e.g., "ba_labels_stop_flag")
            show_stats: Whether to display stats in real-time
            stats_formatter: Optional function to format stats for display (receives stats dict)
        """
        self.stop_flag_key = stop_flag_key
        self.show_stats = show_stats
        self.stats_formatter = stats_formatter
        
        # Create placeholders for UI updates
        self.progress_placeholder = st.empty()
        self.status_placeholder = st.empty()
        self.stats_placeholder = st.empty() if show_stats else None
    
    def progress_callback(self, message: str, status: str = "info"):
        """
        Display progress messages in the UI.
        
        Args:
            message: Message to display
            status: Message type - "info", "success", "warning", or "error"
        """
        if status == "error":
            self.status_placeholder.error(message)
        elif status == "warning":
            self.status_placeholder.warning(message)
        elif status == "success":
            self.status_placeholder.success(message)
        else:
            self.progress_placeholder.info(message)
    
    def stop_flag_callback(self) -> bool:
        """
        Check if user clicked stop button.
        
        Returns:
            bool: True if stop was requested, False otherwise
        """
        return st.session_state.get(self.stop_flag_key, False)
    
    def stats_callback(self, stats: dict):
        """
        Update stats display in real-time.
        
        Args:
            stats: Dictionary containing download statistics
        """
        if self.show_stats and self.stats_placeholder:
            if self.stats_formatter:
                # Use custom formatter if provided
                formatted_message = self.stats_formatter(stats)
                self.stats_placeholder.info(formatted_message)
            # If no formatter provided, don't display anything (silent mode)


def create_download_callbacks(stop_flag_key: str, show_stats: bool = False, stats_formatter=None):
    """
    Factory function to create download callbacks.
    
    Args:
        stop_flag_key: Session state key for the stop flag
        show_stats: Whether to display stats in real-time
        stats_formatter: Optional function to format stats for display
    
    Returns:
        tuple: (progress_callback, stop_flag_callback, stats_callback)
    """
    callbacks = DownloadCallbacks(stop_flag_key, show_stats, stats_formatter)
    return (
        callbacks.progress_callback,
        callbacks.stop_flag_callback,
        callbacks.stats_callback
    )
