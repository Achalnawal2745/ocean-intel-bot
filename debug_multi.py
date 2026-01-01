import requests
import json

URL = "http://127.0.0.1:8000/query"
query = "path of floats 1902669 and 1902670"

print(f"Testing Query: '{query}'")
resp = requests.post(URL, json={"query": query, "session_id": "debug_multi"})

if resp.status_code == 200:
    data = resp.json()
    formats = data.get("formats", {})
    map_data = formats.get("map")
    
    if map_data:
        print(f"Map Type: {map_data.get('type')}")
        print(f"Map Data Keys: {list(map_data.get('data', {}).keys())}")
        
        if map_data.get("type") == "multiple_trajectories":
            m_data = map_data.get("data", {})
            if "trajectories" not in m_data:
                print("!!! ERROR REPRODUCED: 'trajectories' key missing in map_data['data']")
            else:
                print("SUCCESS: 'trajectories' key found.")
    else:
        print("No map data found in response.")
else:
    print(f"Error: {resp.status_code}")
