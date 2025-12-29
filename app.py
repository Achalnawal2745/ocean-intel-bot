"""
ARGO Ocean Intelligence - Streamlit Frontend
AI-powered conversational interface for ARGO float data
"""

import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="🌊 ARGO Ocean Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# Sidebar
with st.sidebar:
    st.markdown("### 🌊 ARGO Ocean Intelligence")
    st.markdown("---")
    
    # System status
    st.markdown("#### System Status")
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=5).json()
        if health.get("status") == "healthy":
            st.success("✅ Backend Online")
            st.metric("Tools Available", health.get("tools_available", 0))
            st.metric("Active Sessions", health.get("memory_sessions", 0))
        else:
            st.error("❌ Backend Offline")
    except:
        st.error("❌ Cannot connect to backend")
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("#### Quick Actions")
    
    if st.button("🗺️ Show All Floats"):
        st.session_state.messages.append({
            "role": "user",
            "content": "show all floats on map"
        })
        st.rerun()
    
    if st.button("📊 Indian Ocean Stats"):
        st.session_state.messages.append({
            "role": "user",
            "content": "show floats in indian ocean and their salinity on graph"
        })
        st.rerun()
    
    if st.button("🌡️ Temperature Trends"):
        st.session_state.messages.append({
            "role": "user",
            "content": "compare temperature for floats in indian ocean"
        })
        st.rerun()
    
    st.markdown("---")
    
    # Example queries
    with st.expander("💡 Example Queries"):
        st.markdown("""
        - Show floats in Arabian Sea
        - Temperature depth profile for float 1902669
        - Compare salinity for floats 1902669 and 1902670
        - Show trajectory of float 2900565
        - List all floats
        - Floats near equator
        """)
    
    st.markdown("---")
    
    # Admin section
    with st.expander("⚙️ Admin: Add Float"):
        float_id = st.text_input("Float ID", placeholder="e.g., 2900565")
        if st.button("Download & Ingest"):
            if float_id:
                with st.spinner("Downloading..."):
                    try:
                        dl_response = requests.post(
                            f"{BACKEND_URL}/admin/download-float",
                            json={"float_id": float_id},
                            timeout=120
                        )
                        dl_result = dl_response.json()
                        
                        if dl_result.get("success"):
                            st.success(f"✅ {dl_result['message']}")
                            
                            with st.spinner("Ingesting..."):
                                ing_response = requests.post(
                                    f"{BACKEND_URL}/admin/ingest-float",
                                    json={"float_id": float_id},
                                    timeout=120
                                )
                                ing_result = ing_response.json()
                                
                                if ing_result.get("success"):
                                    st.success(f"✅ {ing_result['message']}")
                                    st.info(f"📊 {ing_result['profiles_count']} profiles, {ing_result['measurements_count']} measurements")
                                else:
                                    st.error(f"❌ {ing_result.get('message', 'Ingestion failed')}")
                        else:
                            st.error(f"❌ {dl_result.get('message', 'Download failed')}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("Please enter a float ID")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Main content
st.markdown('<div class="main-header">🌊 ARGO Ocean Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Conversational Interface for Ocean Data</div>', unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display visualizations if available
        if message["role"] == "assistant" and "data" in message:
            data = message["data"]
            
            # Display text response
            ai_response = data.get("text", "I processed your request.")
            st.markdown(ai_response)
                
            # Iterate over standardized visualizations
            visualizations = data.get("visualizations", [])
            
            if visualizations:
                # Determine layout based on counts
                maps = [v for v in visualizations if v["type"] == "map"]
                graphs = [v for v in visualizations if v["type"] == "graph"]
                
                # Create containers/columns
                if maps and graphs:
                    col1, col2 = st.columns(2)
                elif maps or graphs:
                    col1 = st.container()
                    col2 = None
                else:
                    col1 = col2 = None

                    # Render Maps
                    if maps:
                         with col1 if col2 else st.container():
                            st.markdown(f"#### 🗺️ {maps[0].get('title', 'Map View')}")
                            map_data = maps[0]["data"] # Take first map for now
                            
                            m = folium.Map(location=[0, 80], zoom_start=3)
                            
                            if map_data["type"] == "markers":
                                for marker in map_data["data"]["markers"]:
                                    folium.Marker(
                                        location=[marker["lat"], marker["lon"]],
                                        popup=f"<b>{marker['name']}</b>",
                                        tooltip=marker["name"]
                                    ).add_to(m)
                            
                            elif map_data["type"] in ["trajectory", "multiple_trajectories", "trajectory_map"]:
                                if map_data["type"] == "trajectory":
                                    trajectories = [map_data["data"]]
                                elif map_data["type"] == "trajectory_map":
                                    trajectories = map_data.get("trajectories", [])
                                else:
                                    trajectories = list(map_data["data"].get("trajectories", {}).values())
                                
                                colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'darkblue']
                                for idx, traj in enumerate(trajectories):
                                    if "trajectory" in traj:
                                        points = [(p["latitude"], p["longitude"]) for p in traj["trajectory"]]
                                    elif "points" in traj:
                                        points = [(p.get("lat") or p.get("latitude"), p.get("lon") or p.get("longitude")) for p in traj["points"]]
                                    else:
                                        continue
                                    
                                    color = colors[idx % len(colors)]
                                    folium.PolyLine(points, color=color, weight=2, opacity=0.8).add_to(m)
                                    if points:
                                        folium.Marker(points[0], icon=folium.Icon(color=color, icon='play')).add_to(m)
                                        folium.Marker(points[-1], icon=folium.Icon(color=color, icon='stop')).add_to(m)
                            
                            st_folium(m, width=700, height=500)

                    # Render Graphs
                    if graphs:
                        with col2 if col2 else st.container():
                            st.markdown(f"#### 📊 {graphs[0].get('title', 'Graph View')}")
                            graph_data = graphs[0]["data"]
                            
                            fig = go.Figure()
                            
                            if graph_data["type"] == "bar_chart":
                                for dataset in graph_data["data"]["datasets"]:
                                    fig.add_trace(go.Bar(
                                        name=dataset["label"],
                                        x=graph_data["data"]["labels"],
                                        y=dataset["values"]
                                    ))
                                fig.update_layout(barmode='group')
                                
                            elif graph_data["type"] == "line_chart":
                                fig.add_trace(go.Scatter(
                                    x=graph_data["data"]["x"],
                                    y=graph_data["data"]["y"],
                                    mode='lines+markers'
                                ))
                            
                            if "data" in graph_data and "parameter" in graph_data["data"]:
                                param = graph_data["data"]["parameter"]
                                fig.update_layout(
                                    title=graphs[0].get("title", ""),
                                    xaxis_title=graph_data["data"].get("x_label", ""),
                                    yaxis_title=graph_data["data"].get("y_label", param),
                                    height=500
                                )
                                
                            st.plotly_chart(fig, use_container_width=True)
                


# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        🌊 ARGO Ocean Intelligence System | Powered by AI & Real-time Ocean Data
    </div>
    """,
    unsafe_allow_html=True
)

# Chat input
if prompt := st.chat_input("Ask about ocean data... (e.g., 'Show floats in Indian Ocean')"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get response from backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/query",
                    json={
                        "query": prompt,
                        "session_id": st.session_state.session_id
                    },
                    timeout=60
                )
                
                data = response.json()
                
                # Store message with data
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data.get("text", "I processed your request."),
                    "data": data
                })
                
                # Rerun to display visualizations via main loop
                st.rerun()
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
