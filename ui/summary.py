# ui/summary.py
import streamlit as st

def render_summary_table(merged_df):
    summary = merged_df.groupby("Location").agg(
        parts_count=("Part", "count"),
        found_parts=("Found", "sum"),
        total_wanted=("Quantity_wanted", "sum")
    ).reset_index()
    summary["completion_%"] = (100 * summary["found_parts"] / summary["total_wanted"]).round(1).fillna(0)

    st.markdown("### 📈 Summary & Progress by Location")
    st.data_editor(
        summary,
        column_config={
            "completion_%": st.column_config.ProgressColumn(
                "completion_%", format="%d%%", min_value=0, max_value=100
            )
        },
        hide_index=True,
        width='stretch'
    )
