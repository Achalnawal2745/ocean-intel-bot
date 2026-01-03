"""
Float Chat - Streamlit Frontend
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
    page_title="🌊 Float Chat -ARGO OCEAN INTELLIGENCE SYSTEM",
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
    st.markdown("### 🌊 Float Chat")
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
st.markdown('<div class="main-header">🌊 Float Chat -ARGO OCEAN INTELLIGENCE SYSTEM</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Conversational Interface for Ocean Data</div>', unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display visualizations if available
        if message["role"] == "assistant" and "data" in message:
            data = message["data"]
            
            # Create columns for side-by-side display
            has_map = data.get("formats", {}).get("map") is not None
            has_graph = data.get("formats", {}).get("graph") is not None
            
            if has_map and has_graph:
                col1, col2 = st.columns(2)
            elif has_map or has_graph:
                col1 = st.container()
                col2 = None
            else:
                col1 = col2 = None
            
            # Display map
            if has_map:
                with col1 if col2 else st.container():
                    st.markdown("#### 🗺️ Map View")
                    map_data = data["formats"]["map"]
                    
                    # Create map
                    m = folium.Map(location=[0, 80], zoom_start=3)
                    
                    if map_data["type"] == "markers":
                        # Add markers
                        for marker in map_data["data"]["markers"]:
                            folium.Marker(
                                location=[marker["lat"], marker["lon"]],
                                popup=f"<b>{marker['name']}</b><br>Lat: {marker['lat']}<br>Lon: {marker['lon']}",
                                tooltip=marker["name"]
                            ).add_to(m)
                    
                    elif map_data["type"] in ["trajectory", "multiple_trajectories"]:
                        # Add trajectories
                        if map_data["type"] == "trajectory":
                            trajectories = [map_data["data"]]
                        else:
                            # Defensive check to handle both list and dict structures
                            traj_dict = map_data.get("data", {}).get("trajectories", {})
                            if isinstance(traj_dict, dict):
                                trajectories = list(traj_dict.values())
                            else:
                                trajectories = traj_dict if isinstance(traj_dict, list) else []
                        
                        colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'darkblue']
                        for idx, traj in enumerate(trajectories):
                            if "trajectory" in traj:
                                points = [(p["latitude"], p["longitude"]) for p in traj["trajectory"]]
                            elif "points" in traj:
                                points = [(p["lat"], p["lon"]) for p in traj["points"]]
                            else:
                                continue
                            
                            color = colors[idx % len(colors)]
                            
                            # Draw trajectory line
                            folium.PolyLine(
                                points,
                                color=color,
                                weight=2,
                                opacity=0.8,
                                popup=f"Float {traj.get('float_id', 'Unknown')}"
                            ).add_to(m)
                            
                            # Add start marker
                            if points:
                                folium.Marker(
                                    points[0],
                                    icon=folium.Icon(color=color, icon='play'),
                                    popup=f"Start: Float {traj.get('float_id', 'Unknown')}"
                                ).add_to(m)
                                
                                # Add end marker
                                folium.Marker(
                                    points[-1],
                                    icon=folium.Icon(color=color, icon='stop'),
                                    popup=f"End: Float {traj.get('float_id', 'Unknown')}"
                                ).add_to(m)
                    
                    st_folium(m, width=700, height=500)
            
            # Display graph
            if has_graph:
                with col2 if col2 else st.container():
                    st.markdown("#### 📊 Graph View")
                    graph_data = data["formats"]["graph"]
                    
                    if graph_data["type"] == "bar_chart":
                        # Create bar chart
                        fig = go.Figure()
                        
                        for dataset in graph_data["data"]["datasets"]:
                            fig.add_trace(go.Bar(
                                name=dataset["label"],
                                x=graph_data["data"]["labels"],
                                y=dataset["values"]
                            ))
                        
                        fig.update_layout(
                            title=f"{graph_data['data']['parameter'].title()} Comparison",
                            xaxis_title="Float ID",
                            yaxis_title=f"{graph_data['data']['parameter'].title()} (PSU)" if graph_data['data']['parameter'] == 'salinity' else graph_data['data']['parameter'].title(),
                            barmode='group',
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif graph_data["type"] == "line_chart":
                        # Create line chart
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=graph_data["data"]["x"],
                            y=graph_data["data"]["y"],
                            mode='lines+markers',
                            name=graph_data["data"].get("title", "Data")
                        ))
                        
                        fig.update_layout(
                            title=graph_data["data"].get("title", "Line Chart"),
                            xaxis_title=graph_data["data"].get("x_label", "X"),
                            yaxis_title=graph_data["data"].get("y_label", "Y"),
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)

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
                
                # Display AI response
                ai_response = data.get("ai_synthesized_response", "")
                if not ai_response:
                    ai_response = "I processed your query. Check the visualizations below!"
                
                st.markdown(ai_response)
                
                # Store message with data
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ai_response,
                    "data": data
                })
                
                # Rerun to display visualizations
                st.rerun()
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

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
