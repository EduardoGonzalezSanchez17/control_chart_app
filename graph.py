import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re 
from pathlib import Path



st.sidebar.image("https://www.aftermarket.astemo.com/americas/en/ourbusiness/assets/img/A_Logo_Red.png", width="stretch")
#st.sidebar.image("https://www.aftermarket.astemo.com/apac/en/assets/img/ourbusiness/img_container_03.png", width="stretch")


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
    usecols=["id", "two_d_code", "item", "spec_max", "data", "spec_min", "date_time", "machine_code","test_condition_file"]
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
    "TCF"      
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

df["Name"] = pd.to_datetime(df["Name"], errors="coerce")

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
# TCF selector (depends on selected Test Name)
# -----------------------------------

st.sidebar.markdown(
    "<span style='font-weight:600'>Select TCF</span>",
    unsafe_allow_html=True
)

tcf_options = sorted(
    df[df["Test_Name_Normalized"] == test_selected]["TCF"].astype(str).unique()
)

tcf_options = tcf_options + ["ALL"]

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

module_options = module_options + ["ALL"]

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

machine_options = machine_options + ["ALL"]

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

# -----------------------------------
# Plot Control Chart
# -----------------------------------
fig = go.Figure()

# Within spec

fig.add_trace(go.Scatter(
    x=df_filt.loc[~df_filt["Out_Of_Limit"], "Index"],
    y=df_filt.loc[~df_filt["Out_Of_Limit"], "Value"],
    mode="markers",
    name="Within spec",
    marker=dict(color="blue", size=5),
    customdata=df_filt.loc[~df_filt["Out_Of_Limit"], "ID"],
    hovertemplate=(
        #"Index: %{x}<br>"
        "ID: %{customdata}<br>"
        "Value: %{y}"
        "<extra></extra>"
    )
))


# Out of spec
fig.add_trace(go.Scatter(
    x=df_filt.loc[df_filt["Out_Of_Limit"], "Index"],
    y=df_filt.loc[df_filt["Out_Of_Limit"], "Value"],
    mode="markers",
    name="Out of spec",
    marker=dict(color="red", size=7),
    customdata=df_filt["ID"],
    hovertemplate=(
	#"Index=%{x}<br>"
	"ID: %{customdata}<br>"
	"Value=%{y}"
    	"<extra></extra>" 
    )
))

# Limit Max
fig.add_trace(go.Scatter(
    x=df_filt["Index"],
    y=df_filt["Limit_Max"],
    mode="lines",
    name="Limit Max",
    line=dict(color="orange", dash="dash")
))

# Limit Min
fig.add_trace(go.Scatter(
    x=df_filt["Index"],
    y=df_filt["Limit_Min"],
    mode="lines",
    name="Limit Min",
    line=dict(color="green", dash="dash")
))


STEP = max(1, len(df_filt) // 10)

tick_vals = df_filt["Index"][::STEP]
tick_text = df_filt["Name"][::STEP].dt.strftime("%Y-%m-%d %H:%M")

# -----------------------------------
# Layout & interaction
# -----------------------------------
fig.update_layout(
    title="Control Chart",
    title_x=0.5,

    xaxis=dict(
        title="Date / Item",
        tickmode="array",
        tickvals=tick_vals,
        ticktext=tick_text,
        tickangle=-45         
    ),

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
    margin=dict(l=40, r=50, t=60, b=90)
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
        f"<span style='color:red'>●</span> Out of spec : {out_of_spec_count}"
    )
)

# -----------------------------------
# Show plot
# -----------------------------------
st.plotly_chart(fig, width="stretch")


st.markdown(f"""
### Selection Summary

- **Model:** `{model}`  
- **Event:** `{event}`  
- **Test Name:** `{test_selected}`  
- **TCF:** `{tcf_selected}`  
- **Module Code:** `{product_selected}`  
- **Machine Code:** `{machine_selected}`  
""")


st.divider()

st.caption(
    "BECM · PV 2-5 Data Analysis · v1.0"
)

