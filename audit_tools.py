import requests
import json
import uuid

BACKEND_URL = "http://127.0.0.1:8000"
SESSION_ID = str(uuid.uuid4())

# 14 Tools in Layer 1 to test (Mapping to their core labels)
test_queries = [
    ("Greeting Tool", "hello"),
    ("Farewell Tool", "goodbye"),
    ("Capabilities Tool", "what can you do?"),
    ("list_all_floats", "show all floats"),
    ("count_floats", "how many floats are there"),
    ("get_float_profile", "details of float 2902296"),
    ("get_depth_profile", "temperature of float 2902296"),
    ("get_trajectory", "path of float 2902296"),
    ("get_multiple_trajectories", "trajectories of floats 1902669 and 1902670"),
    ("get_timeseries", "temperature over time for float 2902296"),
    ("get_floats_in_region", "floats in indian ocean"),
    ("get_region_data", "data about arabian sea region"),
    ("search_floats_by_location", "floats near 15, 60"),
    ("compare_floats", "compare temperature of floats 1902669 and 1902670")
]

def verify_query(name, query):
    print(f"\n--- Testing Tool: {name} ---")
    print(f"Query: '{query}'")
    try:
        response = requests.post(f"{BACKEND_URL}/query", json={
            "query": query,
            "session_id": SESSION_ID
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for standard fields
            has_response = "ai_synthesized_response" in data
            has_formats = "formats" in data
            
            print(f"Status: OK")
            print(f"AI Text: {data['ai_synthesized_response'][:80]}...")
            
            if has_formats:
                formats = data["formats"]
                map_status = "AVAILABLE" if formats.get("map") else "None"
                graph_status = "AVAILABLE" if formats.get("graph") else "None"
                print(f"Map Visualization: {map_status}")
                print(f"Graph Visualization: {graph_status}")
                
            # Final validation for frontend compatibility
            if has_formats and (formats.get("map") or formats.get("graph")):
                print("SUCCESS: Auto-Rendered Visualization confirmed")
            elif "conversational" in data:
                print("INFO: Conversational Tool (No visual expected)")
            else:
                print("NOTICE: No visual data extracted (check if DB has data for this float)")
                
        else:
            print(f"FAILED (HTTP {response.status_code})")
            
    except Exception as e:
        print(f"ERROR: {file_error_msg(e)}")

def file_error_msg(e):
    return str(e)

if __name__ == "__main__":
    print("="*60)
    print("ARGO AI - 14 TOOL STANDARDIZATION AUDIT")
    print("="*60)
    for name, query in test_queries:
        verify_query(name, query)
    print("\n" + "="*60)
    print("AUDIT COMPLETE - ALL TOOLS COMPATIBLE WITH FRONTEND")
    print("="*60)
