import requests
import json

URL = "http://127.0.0.1:8000/query"
query = "show location of all floats in indian ocean"
print(f"Testing Query: '{query}'")
resp = requests.post(URL, json={"query": query, "session_id": "test_map"})

if resp.status_code == 200:
    data = resp.json()
    formats = data.get("formats", {})
    map_data = formats.get("map")
    
    print(f"\n=== RESPONSE STRUCTURE ===")
    print(f"Response Type: {data.get('response_type')}")
    print(f"Has Map Data: {map_data is not None}")
    
    if map_data:
        print(f"\n=== MAP DATA ===")
        print(f"Map Type: {map_data.get('type')}")
        print(f"Map Data Keys: {list(map_data.get('data', {}).keys())}")
        
        m_data = map_data.get('data', {})
        trajs = m_data.get('trajectories')
        
        if trajs:
            print(f"\n=== TRAJECTORIES ===")
            print(f"Type: {type(trajs)}")
            if isinstance(trajs, dict):
                print(f"Number of floats: {len(trajs)}")
                for fid, traj in list(trajs.items())[:2]:  # Show first 2
                    print(f"\nFloat {fid}:")
                    print(f"  Keys: {list(traj.keys())}")
                    if 'points' in traj:
                        print(f"  Points count: {len(traj['points'])}")
                        if traj['points']:
                            print(f"  First point: {traj['points'][0]}")
            elif isinstance(trajs, list):
                print(f"Number of trajectories: {len(trajs)}")
                if trajs:
                    print(f"First trajectory keys: {list(trajs[0].keys())}")
        else:
            print("No trajectories found!")
    
    # Check raw_result structure
    raw_result = data.get('raw_result', {})
    if raw_result and isinstance(raw_result, dict):
        print(f"\n=== RAW RESULT (Before Standardization) ===")
        print(f"Raw Result Keys: {list(raw_result.keys())}")
        if 'result' in raw_result:
            result_obj = raw_result['result']
            if isinstance(result_obj, dict):
                print(f"Result Keys: {list(result_obj.keys())}")
                if 'type' in result_obj:
                    print(f"Result Type: {result_obj.get('type')}")
                if 'trajectories' in result_obj:
                    raw_trajs = result_obj['trajectories']
                    if isinstance(raw_trajs, dict):
                        first_fid = list(raw_trajs.keys())[0]
                        print(f"First trajectory keys: {list(raw_trajs[first_fid].keys())}")
    else:
        print("No map data in response!")
        print(f"\nFull response keys: {list(data.keys())}")
else:
    print(f"Error: {resp.status_code}")
