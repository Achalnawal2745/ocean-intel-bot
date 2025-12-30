import requests
import json

URL = "http://127.0.0.1:8000/query"
query = "trajectories of floats 1902669 and 1902670"

resp = requests.post(URL, json={"query": query, "session_id": "audit_multi"})
if resp.status_code == 200:
    data = resp.json()
    f = data.get("formats", {}).get("map", {})
    trajs = f.get("data", {}).get("trajectories", {})
    print(f"Type: {f.get('type')}")
    print(f"Trajectories Count: {len(trajs)}")
    if trajs:
        first_fid = list(trajs.keys())[0]
        first_traj = trajs[first_fid]
        pts = first_traj.get("points", [])
        print(f"First Traj ({first_fid}) Points: {len(pts)}")
        if pts:
            print(f"First Point Example: {pts[0]}")
            has_lat_lon = "lat" in pts[0] and "lon" in pts[0]
            print(f"Has lat/lon: {has_lat_lon}")
else:
    print(f"Error: {resp.status_code}")
