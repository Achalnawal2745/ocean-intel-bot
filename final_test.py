import requests
import json

URL = "http://127.0.0.1:8000/query"

# Test both Layer 1 and Layer 2 queries
test_queries = [
    ("Layer 1 (Direct)", "path of floats 1902669 and 1902670"),
    ("Layer 2 (Orchestration)", "show location of all floats in indian ocean")
]

for layer_name, query in test_queries:
    print(f"\n{'='*60}")
    print(f"Testing {layer_name}: '{query}'")
    print('='*60)
    
    resp = requests.post(URL, json={"query": query, "session_id": "final_test"})
    
    if resp.status_code == 200:
        data = resp.json()
        formats = data.get("formats", {})
        map_data = formats.get("map")
        
        if map_data:
            print(f"[OK] Map Type: {map_data.get('type')}")
            
            if map_data.get("type") == "multiple_trajectories":
                m_data = map_data.get('data', {})
                trajs = m_data.get('trajectories', {})
                
                if isinstance(trajs, dict):
                    print(f"[OK] Trajectories: {len(trajs)} floats")
                    
                    # Check first trajectory structure
                    first_fid = list(trajs.keys())[0]
                    first_traj = trajs[first_fid]
                    
                    if 'float_id' in first_traj and 'points' in first_traj:
                        points_count = len(first_traj['points'])
                        print(f"[OK] Structure: Correct (float_id + points)")
                        print(f"[OK] Points: {points_count} points for float {first_fid}")
                        
                        if points_count > 0:
                            print(f"[OK] First point: {first_traj['points'][0]}")
                            print(f"\n[SUCCESS] {layer_name} - WORKING PERFECTLY!")
                        else:
                            print(f"[FAIL] {layer_name} - NO POINTS EXTRACTED!")
                    else:
                        print(f"[FAIL] {layer_name} - WRONG STRUCTURE: {list(first_traj.keys())}")
                else:
                    print(f"[FAIL] {layer_name} - Trajectories is not a dict: {type(trajs)}")
        else:
            print(f"[FAIL] {layer_name} - NO MAP DATA")
    else:
        print(f"[FAIL] Error: {resp.status_code}")

print(f"\n{'='*60}")
print("FINAL VERDICT:")
print('='*60)
