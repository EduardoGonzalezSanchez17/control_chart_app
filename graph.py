import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re 
from pathlib import Path
from scipy.stats import norm
import numpy as np
import plotly.io as pio

import sys
import warnings

if "warnings" not in sys.modules:
    import warnings



st.set_page_config(
    page_title="BECM PV analysis",
    layout="wide"
)

st.sidebar.image("https://www.aftermarket.astemo.com/americas/en/ourbusiness/assets/img/A_Logo_Red.png", width="stretch")
#st.sidebar.image("https://www.aftermarket.astemo.com/apac/en/assets/img/ourbusiness/img_container_03.png", width="stretch")
#st.sidebar.image("https://www.astemo.com/en/assets/images/top/kv_img02.jpg", width="stretch")



# -----------------------------------
# Load data
# -----------------------------------
st.sidebar.header("Load Excel File")

uploaded_file = st.sidebar.file_uploader(
    "Select Excel file",
    type=["CSV"]
)

if uploaded_file is None:
    st.info("Please select an Excel file to continue.")

intro_placeholder = st.empty()

if uploaded_file is None:
    intro_placeholder.markdown(
        """
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 30px;
        ">
            <img src="https://www.aftermarket.astemo.com/americas/en/ourbusiness/assets/img/A_Logo_Red.png"
                 style="max-width: 220px;">
            <p style="margin-top: 10px; font-size: 18px; font-weight: 600;">
                BECM team
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()
else:
    intro_placeholder.empty()

df = pd.read_csv(
    uploaded_file,
    usecols=["id", "two_d_code", "item", "spec_max", "data", "spec_min", "date_time", "machine_code","test_condition_file","lap_time"]
)

df.columns = [
    "ID", #
    "Module_Code", 
    "Test_Name",  
    "Limit_Max",      
    "Value",         
    "Limit_Min",      
    "Name",           # DATE
    "Machine_Code",   
    "TCF",
    "lap_time"
]


filename_stem = Path(uploaded_file.name).stem
parts = filename_stem.split("_")

model = parts[0] if len(parts) > 0 else "N/A"
event = parts[1] if len(parts) > 1 else "N/A"


# -----------------------------------
# Normalize Test Name (remove Mode_xx_ prefix)
# -----------------------------------
df["Test_Name_Normalized"] = df["Test_Name"].str.replace(
    r"^Mode_\d+_",
    "",
    regex=True
)



# Convert data_time to datetime (CSV format: YYYY/MM/DD HH:MM:SS)
df["Name"] = pd.to_datetime(
    df["Name"],
    format="%Y/%m/%d %H:%M:%S",
    errors="raise"   # ahora sí conviene usar raise
)

df["lap_time"] = pd.to_numeric(df["lap_time"], errors="coerce")
df["End_Time"] = df["Name"] + pd.to_timedelta(df["lap_time"], unit="s")
df["End_Time"] = df["End_Time"].dt.floor("s")


# -----------------------------------
# Sidebar selectors
# -----------------------------------
st.sidebar.title("Filters")

# -----------------------------------
# Order Test Names by Out-of-Spec count (descending)
# -----------------------------------

# Calculate Out Of Spec for each row
df_oos = df.assign(
    Out_Of_Limit=(df["Value"] > df["Limit_Max"]) | (df["Value"] < df["Limit_Min"])
)

# Count Out Of Spec occurrences per Test Name
out_of_spec_by_test = (
    df_oos
    .groupby("Test_Name_Normalized")["Out_Of_Limit"]
    .sum()
    .sort_values(ascending=False)
)

# Ordered Test Names (most Out Of Spec first)
test_names_sorted = out_of_spec_by_test.index.astype(str).tolist()

# -----------------------------------
# Extract numbering range from Excel file name (e.g. *_6_10)
# -----------------------------------
filename = Path(uploaded_file.name).stem
match = re.search(r"_(\d+)_(\d+)$", filename)


if match:
    top_range_text = f"TOP ({match.group(1)}–{match.group(2)})"
else:
    top_range_text = ""


if match:
    selectbox_label = f"Select Test Name Top ({match.group(1)}–{match.group(2)})"
else:
    selectbox_label = "Select Test Name"

if match:
    start_num = int(match.group(1))
else:
    start_num = 1  # default start if pattern not found

# -----------------------------------
# Build numbered selectbox options
# -----------------------------------
test_options = [
    f"{start_num + i}. {name} ({int(out_of_spec_by_test[name])})"
    for i, name in enumerate(test_names_sorted)
]


st.sidebar.markdown(
    f"""
    <span style="font-weight:600">
        Select Test Name
    </span>
    <span style="color:red; font-weight:600">
        {top_range_text}
    </span>
    """,
    unsafe_allow_html=True
)

# -----------------------------------
# Test Name selector (numbered)
# -----------------------------------

test_selected_labeled = st.sidebar.selectbox(
    "Select Test Name",
    test_options,
    label_visibility="collapsed"
)

# Extract the real Test Name (without the number)
test_selected = test_selected_labeled.split(". ", 1)[1].rsplit(" (", 1)[0]

# -----------------------------------
# FILTERS
# -----------------------------------
st.sidebar.markdown(
    "<span style='font-weight:600'>Select TCF</span>",
    unsafe_allow_html=True
)

tcf_options = sorted(
    df[df["Test_Name_Normalized"] == test_selected]["TCF"].astype(str).unique()
)
tcf_options += ["ALL"]

tcf_selected = st.sidebar.selectbox(
    "Select TCF",
    tcf_options,
    label_visibility="collapsed"
)

st.sidebar.markdown(
    "<span style='font-weight:600'>Select Module Code</span>",
    unsafe_allow_html=True
)

module_options = sorted(
    df[
        (df["Test_Name_Normalized"] == test_selected) &
        (df["TCF"] == tcf_selected)
    ]["Module_Code"].astype(str).unique()
)
module_options += ["ALL"]

product_selected = st.sidebar.selectbox(
    "Select Module Code",
    module_options,
    label_visibility="collapsed"
)

st.sidebar.markdown(
    "<span style='font-weight:600'>Select Machine Code</span>",
    unsafe_allow_html=True
)

machine_options = sorted(
    df[
        (df["Test_Name_Normalized"] == test_selected) &
        (df["TCF"] == tcf_selected) &
        (df["Module_Code"] == product_selected)
    ]["Machine_Code"].astype(str).unique()
)
machine_options += ["ALL"]

machine_selected = st.sidebar.selectbox(
    "Select Machine Code",
    machine_options,
    label_visibility="collapsed"
)

# -----------------------------------
# Filter data
# -----------------------------------
df_filt = df[
    ((df["Test_Name_Normalized"] == test_selected) if test_selected != "ALL" else True) &
    ((df["TCF"] == tcf_selected) if tcf_selected != "ALL" else True) &
    ((df["Module_Code"] == product_selected) if product_selected != "ALL" else True) &
    ((df["Machine_Code"] == machine_selected) if machine_selected != "ALL" else True)
].reset_index(drop=True)


if df_filt.empty:
    st.warning("No data for selected Test / Product / Machine")
    st.stop()

# -----------------------------------
# Index + limits detection
# -----------------------------------

df_filt["Index"] = range(len(df_filt))

df_filt["Out_Of_Limit"] = (
    (df_filt["Value"] > df_filt["Limit_Max"]) |
    (df_filt["Value"] < df_filt["Limit_Min"])
)
# -----------------------------------
# Summary values
# -----------------------------------
limit_max_value = df_filt["Limit_Max"].iloc[0]
limit_min_value = df_filt["Limit_Min"].iloc[0]

out_of_spec_count = int(df_filt["Out_Of_Limit"].sum())
within_spec_count = len(df_filt) - out_of_spec_count
# Average value for Out of Spec points
out_of_spec_count = int(df_filt["Out_Of_Limit"].sum())

if out_of_spec_count > 0:
    avg_out_of_spec = df_filt.loc[df_filt["Out_Of_Limit"], "Value"].mean()
else:
    avg_out_of_spec = None

if avg_out_of_spec is not None:
    avg_out_of_spec_text = f"{avg_out_of_spec:.3f}"
else:
    avg_out_of_spec_text = "N/A"


df_filt = df_filt.sort_values("End_Time").reset_index(drop=True)

t0 = df_filt["End_Time"].iloc[0]

df_filt["Hours_From_Start"] = (
    df_filt["End_Time"] - t0
).dt.total_seconds() / 3600
print(df_filt[["End_Time", "Hours_From_Start"]].head(1000))

start_date_main = df_filt["End_Time"].min()
start_date_main_str = start_date_main.strftime("%Y-%m-%d %H:%M:%S")

st.markdown(f"""
## Selection Summary

- **BECM Identifier:** `{model} - {event} - {product_selected}`  
- **Test Name:** `{test_selected}`  
- **TCF:** `{tcf_selected}`  
- **Machine Code:** `{machine_selected}`  
- **Start Date:** `{start_date_main_str}`
""")



# -----------------------------------
# Plot Control Chart
# -----------------------------------
fig = go.Figure()

# Within spec

customdata_within = df_filt.loc[
    ~df_filt["Out_Of_Limit"],
    ["ID", "End_Time"]
].to_numpy()

fig.add_trace(go.Scatter(
    x=df_filt.loc[~df_filt["Out_Of_Limit"], "Hours_From_Start"].to_numpy(),
    y=df_filt.loc[~df_filt["Out_Of_Limit"], "Value"].to_numpy(),
    mode="markers",
    name="Within spec",
    marker=dict(color="blue", size=5),
    customdata=customdata_within,
    hovertemplate=(
        "Test Iteration: %{customdata[0]}<br>"
        "Date: %{customdata[1]|%Y-%m-%d}<br>"
        "Time: %{customdata[1]|%H:%M:%S}<br>"
        "Value: %{y}"
        "<extra></extra>"
    )
))


customdata_oos = df_filt.loc[
    df_filt["Out_Of_Limit"],
    ["ID", "End_Time"]
].to_numpy()

fig.add_trace(go.Scatter(
    x=df_filt.loc[df_filt["Out_Of_Limit"], "Hours_From_Start"].to_numpy(),
    y=df_filt.loc[df_filt["Out_Of_Limit"], "Value"].to_numpy(),
    mode="markers",
    name="Out of spec",
    marker=dict(color="red", size=5),
    customdata=customdata_oos,
    hovertemplate=(
        "Test Iteration: %{customdata[0]}<br>"
        "Date: %{customdata[1]|%Y-%m-%d}<br>"
        "Time: %{customdata[1]|%H:%M:%S}<br>"
        "Value: %{y}"
        "<extra></extra>"
    )
))

# Limit Max
fig.add_trace(go.Scatter(
    x=df_filt["Hours_From_Start"],
    y=df_filt["Limit_Max"],
    mode="lines",
    name="Limit Max",
    line=dict(color="orange", dash="dash")
))

# Limit Min
fig.add_trace(go.Scatter(
    x=df_filt["Hours_From_Start"],
    y=df_filt["Limit_Min"],
    mode="lines",
    name="Limit Min",
    line=dict(color="green", dash="dash")
))



# -----------------------------------
# Layout & interaction
# -----------------------------------

xaxis_config = dict(
    title="Hours from start",
    nticks=12,
    tickformat=".1f",   # o ".2f" 
    automargin=True
)

fig.update_layout(
    title=dict(
        text="<span style='font-weight:700; letter-spacing:0.5px;'>Control Chart</span>",
        x=0.5,
        xanchor="center",
        font=dict(size=22)
    ),

    xaxis=xaxis_config,

    yaxis_title="Value",
    hovermode="closest",
    height=520,
    legend=dict(
        orientation="h",
        x=0.5,
        y=-0.25,
        xanchor="center"
    ),
    showlegend=False,
    margin=dict(l=40, r=50, t=80, b=90) 
)

# -----------------------------------
# Add watermark image (background)
# -----------------------------------
fig.add_layout_image(
    dict(
        source="https://www.aftermarket.astemo.com/americas/en/ourbusiness/assets/img/A_Logo_Red.png", 
        xref="paper", yref="paper",
        x=0.5, y=0.5,               
        sizex=1, sizey=1,            
        xanchor="center", yanchor="middle",
        opacity=0.15,                
        layer="below"                
    )
)
# -----------------------------------
# Right info panel (colored)
# -----------------------------------
fig.add_annotation(
    xref="paper",
    yref="paper",
    x=1.05,
    y=0.15,
    showarrow=False,
    align="left",
    text=(
        f"<span style='color:orange'>--</span> Limit Max : {limit_max_value}<br>"
        f"<span style='color:green'>--</span> Limit Min : {limit_min_value}<br><br>"
        f"<span style='color:blue'>●</span> Within spec : {within_spec_count}<br>"
        f"<span style='color:red'>●</span> Out of spec : {out_of_spec_count}<br>"
        f"<span style='color:red'>─</span> Avg. Out of spec : {avg_out_of_spec_text}"
    )
)


# -----------------------------------
# Show plot
# -----------------------------------
st.plotly_chart(fig, width="stretch")

# -----------------------------------
#Limits to include in CPK
# -----------------------------------

with st.expander("Process Capability (Cpk / PPM)", expanded=False):

    st.markdown("### Process Capability – Data Selection")

    include_within = st.checkbox("Include Within Spec", value=True)
    include_at_min = st.checkbox("Include At Min Limit", value=False)
    include_oos = st.checkbox("Include Out of Spec", value=True)

    within_mask = (
        (df_filt["Value"] > df_filt["Limit_Min"]) &
        (df_filt["Value"] < df_filt["Limit_Max"])
    )

    at_min_mask = (df_filt["Value"] == df_filt["Limit_Min"])

    oos_mask = (
        (df_filt["Value"] < df_filt["Limit_Min"]) |
        (df_filt["Value"] > df_filt["Limit_Max"])
    )

    final_mask = False

    if include_within:
        final_mask |= within_mask

    if include_at_min:
        final_mask |= at_min_mask

    if include_oos:
        final_mask |= oos_mask

    df_cpk = df_filt[final_mask].copy()
    if df_cpk.empty or len(df_cpk) < 2:
        st.warning("Not enough data for capability analysis with current selection.")

    #------------------------------------
    # CPK built
    #------------------------------------

    # Mean and standard deviation
    mean_cpk = df_cpk["Value"].mean()
    std_cpk = df_cpk["Value"].std(ddof=1)

    # Validación básica
    if std_cpk == 0 or pd.isna(std_cpk):
        cpk_value = None
    else:
        cpk_upper = (limit_max_value - mean_cpk) / (3 * std_cpk)
        cpk_lower = (mean_cpk - limit_min_value) / (3 * std_cpk)

        cpk_value = min(cpk_upper, cpk_lower)

    #------------------------------------
    # PPM built
    #------------------------------------

    if cpk_value is not None and std_cpk > 0:
        ppm_lower = norm.cdf(limit_min_value, mean_cpk, std_cpk) * 1_000_000
        ppm_upper = (1 - norm.cdf(limit_max_value, mean_cpk, std_cpk)) * 1_000_000
        ppm_total = ppm_lower + ppm_upper
    else:
        ppm_total = None

    # -----------------------------------
    # KPI TAGS
    # -----------------------------------
    col1, col2 = st.columns(2)

    if cpk_value is not None:
        col1.metric("Cpk", f"{cpk_value:.2f}")
    else:
        col1.metric("Cpk", "N/A")

    if ppm_total is not None:
        col2.metric("PPM", f"{ppm_total:,.0f}")
    else:
        col2.metric("PPM", "N/A")

    # -----------------------------------
    # PLOT NORMAL (Capability Chart)
    # -----------------------------------
    if df_cpk.empty or len(df_cpk) < 2:
        st.info(
            "Capability chart cannot be displayed because there is not enough data "
            "with the current selection."
        )

    elif std_cpk <= 0 or pd.isna(std_cpk):
        st.warning(
            "Standard deviation is zero. "
            "Capability chart cannot be generated."
        )

    else:
        values = df_cpk["Value"].to_numpy()

        # Build full X range (data + limits)
        x_min = min(values.min(), limit_min_value)
        x_max = max(values.max(), limit_max_value)

        x_range = np.linspace(x_min, x_max, 400)
        pdf = norm.pdf(x_range, mean_cpk, std_cpk)

        cap_fig = go.Figure()

        # Histogram
        cap_fig.add_trace(go.Histogram(
            x=values,
            nbinsx=30,
            histnorm="probability density",
            name="Data",
            marker_color="steelblue",
            opacity=0.7
        ))

        # Normal distribution
        cap_fig.add_trace(go.Scatter(
            x=x_range,
            y=pdf,
            mode="lines",
            name="Normal Distribution",
            line=dict(color="black", width=2)
        ))

        # Spec limits and mean
        cap_fig.add_vline(
            x=limit_min_value,
            line=dict(color="green", dash="dash"),
            annotation_text="LSL",
            annotation_position="top"
        )

        cap_fig.add_vline(
            x=limit_max_value,
            line=dict(color="orange", dash="dash"),
            annotation_text="USL",
            annotation_position="top"
        )

        cap_fig.add_vline(
            x=mean_cpk,
            line=dict(color="red", dash="dot"),
            annotation_text="Mean",
            annotation_position="top"
        )

        # Axis padding (visual breathing room)
        pad = (x_max - x_min) * 0.05

        cap_fig.update_layout(
            title="Process Capability Distribution",
            xaxis=dict(
                title="Value",
                range=[x_min - pad, x_max + pad]
            ),
            yaxis=dict(
                title="Density"
            ),
            height=420,
            showlegend=True
        )

        st.plotly_chart(cap_fig, width='stretch')

# =====================================================
# GOLDEN PLOTS – EXPORT (COLAPSABLE)
# =====================================================

st.divider()

with st.expander("Golden Plot Export", expanded=False):

    st.markdown("### Golden Plot Export")

    output_path_input = st.text_input(
        "Folder where images will be saved",
        value="Enter a valid path"
    )

    col_range_1, col_range_2 = st.columns(2)

    top_start = col_range_1.number_input(
        "Top start",
        min_value=1,
        value=1,
        step=1
    )

    top_end = col_range_2.number_input(
        "Top end",
        min_value=1,
        value=10,
        step=1
    )


    # ---- TCF selector ----
    tcf_export = st.selectbox(
        "TCF for export",
        sorted(df["TCF"].astype(str).unique()+["ALL"])
    )


    module_mode = st.radio(
        "Module Code for export",
        ["Any", "All"],
        horizontal=True
    )



    if st.button("Generate Golden Plots"):

        if top_start > top_end:
            st.error("Top start must be less than or equal to Top end.")
            st.stop()

        output_dir = Path(output_path_input)
        output_dir.mkdir(parents=True, exist_ok=True)

        top_tests = (
            df.assign(
                OOS=(df["Value"] > df["Limit_Max"]) |
                    (df["Value"] < df["Limit_Min"])
            )
            .groupby("Test_Name_Normalized")["OOS"]
            .sum()
            .sort_values(ascending=False)
            .iloc[top_start - 1 : top_end]
        )

        if top_end - top_start > 500:
            st.warning("Very large range selected. This may take a few minutes.")

        for i, test_name in enumerate(top_tests.index, start=top_start):

            df_tmp = df[df["Test_Name_Normalized"] == test_name].copy()

            # ---- Apply TCF filter ----
            if tcf_export != "ALL":
                df_tmp = df_tmp[df_tmp["TCF"] == tcf_export]

            # ---- Module Code ----

            if module_mode == "Any":
               # Pick ONE random module
               available_modules = df_tmp["Module_Code"].unique()
               available_modules = [m for m in available_modules if m != "ALL"]
    
               if len(available_modules) == 0:
                   continue

               selected_module = np.random.choice(available_modules)
               df_tmp = df_tmp[df_tmp["Module_Code"] == selected_module]
               module_label = selected_module

            elif module_mode == "All":
                # Use ALL modules → no filter
                module_label = "ALL"

	    # ------ Machine code ----------
            if tcf_export == "ALL":
                machine_label = "ALL"
            else:
                machine_values = df_tmp["Machine_Code"].dropna().unique()
                machine_label = machine_values[0]

            if df_tmp.empty:
                continue

            df_tmp = df_tmp.sort_values("End_Time").reset_index(drop=True)

            t0 = df_tmp["End_Time"].iloc[0]
            df_tmp["Hours_From_Start"] = (
                df_tmp["End_Time"] - t0
            ).dt.total_seconds() / 3600

            fig_tmp = go.Figure()

            oos = (
                (df_tmp["Value"] > df_tmp["Limit_Max"]) |
                (df_tmp["Value"] < df_tmp["Limit_Min"])
            )


            limit_max_value = df_tmp["Limit_Max"].iloc[0]
            limit_min_value = df_tmp["Limit_Min"].iloc[0]


            fig_tmp.add_trace(go.Scatter(
                x=df_tmp.loc[~oos, "Hours_From_Start"].to_numpy(),
                y=df_tmp.loc[~oos, "Value"].to_numpy(),
                mode="markers",
                marker=dict(color="blue", size=5),
                name="Within Spec",
            ))

            fig_tmp.add_trace(go.Scatter(
                x=df_tmp.loc[oos, "Hours_From_Start"].to_numpy(),
                y=df_tmp.loc[oos, "Value"].to_numpy(),
                mode="markers",
                marker=dict(color="red", size=5),
                name="Out of Spec",
            ))

            fig_tmp.add_trace(go.Scatter(
                x=df_tmp["Hours_From_Start"].to_numpy(),
                y=df_tmp["Limit_Max"].to_numpy(),
                mode="lines",
                line=dict(color="orange", dash="dash"),
                name=f"Limit Max = {limit_max_value:.3f}",
            ))

            fig_tmp.add_trace(go.Scatter(
                x=df_tmp["Hours_From_Start"].to_numpy(),
                y=df_tmp["Limit_Min"].to_numpy(),
                mode="lines",
                line=dict(color="green", dash="dash"),
                name=f"Limit Min = {limit_min_value:.3f}",
            ))


            start_date = df_tmp["End_Time"].min()
            start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")


            fig_tmp.add_annotation(
            xref="paper",
            yref="paper",
            x=0.01,
            y=1.2,          
            yanchor="top",
            showarrow=False,
            align="left",
            bgcolor="rgba(255,255,255,0.85)", 
            bordercolor="black",
            borderwidth=1,
            font=dict(size=12, color="#003366"),
            text=(
                f"<b>BECM:</b> {model} - {event} - {module_label}<br>"
                f"<b>Test Name:</b> {test_name}<br>"
                f"<b>TCF:</b> {df_tmp['TCF'].iloc[0]}<br>"
                f"<b>Machine:</b> {machine_label}<br>"
                f"<b>Start Date:</b> {start_date_str}"
                )
            )
            
            fig_tmp.add_layout_image(
                dict(
                    source="https://www.aftermarket.astemo.com/americas/en/ourbusiness/assets/img/A_Logo_Red.png",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    sizex=0.6,
                    sizey=0.6,
                    xanchor="center",
                    yanchor="middle",
                    opacity=0.08,          
                    layer="below"          
                ),
            )

            fig_tmp.update_layout(


                xaxis=dict(
                    title=dict(
                        text="<b>Hours from Start</b>",
                        font=dict(size=14)
                    ),
                    tickfont=dict(size=12)
                ),
                yaxis=dict(
                    title=dict(
                        text="<b>Value</b>",
                        font=dict(size=14)
                    ),
                    tickfont=dict(size=12)
                ),
                title=dict(
                    text="Control Chart",
                    x=0.5,
                    xanchor="center",
                    font=dict(size=18)
                ),

                margin=dict(
                    l=60,
                    r=40,
                    t=140,
                    b=60
                ),
                width=1200,
                height=700,
                showlegend=True

            )

            safe_test_name = re.sub(r'[\\/*?:"<>|]', "_", test_name)
            filename = f"{i:02d}_{safe_test_name}.png"

            pio.write_image(
                fig_tmp,
                str(output_dir / filename),
                engine="kaleido"
            )

        st.success("Golden plots generated successfully ✅")




st.divider()

st.caption(
    "BECM · PV 2-5 Data Analysis · v1.0"
)