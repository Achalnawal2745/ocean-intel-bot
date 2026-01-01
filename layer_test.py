"""
Comprehensive test to verify all 3 layers return unified format
Tests Layer 1, Layer 2, and Layer 3 queries
"""
import requests
import json
import time

URL = "http://127.0.0.1:8000/query"

# Test queries for each layer
test_cases = [
    {
        "layer": "Layer 1 - Direct Tool",
        "query": "show float 2902296",
        "expected": "Single float info (text/map)"
    },
    {
        "layer": "Layer 1 - Multiple Trajectories",
        "query": "path of floats 1902669 and 1902670",
        "expected": "2 trajectory paths (map)"
    },
    {
        "layer": "Layer 2 - Orchestration",
        "query": "show location of all floats in indian ocean",
        "expected": "8 trajectory paths (map)"
    },
    {
        "layer": "Layer 3 - SQL Fallback",
        "query": "average temperature at 100m depth",
        "expected": "Graph or text analysis"
    }
]

print("="*70)
print("TESTING ALL 3 LAYERS - UNIFIED FORMAT VERIFICATION")
print("="*70)

results = []

for idx, test in enumerate(test_cases):
    print(f"\n{'='*70}")
    print(f"TEST: {test['layer']}")
    print(f"Query: '{test['query']}'")
    print(f"Expected: {test['expected']}")
    print('='*70)
    
    try:
        resp = requests.post(URL, json={"query": test['query'], "session_id": "layer_test"}, timeout=120)
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Check unified format
            has_formats = "formats" in data
            has_text = data.get("ai_synthesized_response", "") != ""
            response_type = data.get("response_type", "unknown")
            
            print(f"\n[STRUCTURE CHECK]")
            print(f"  Has 'formats' key: {has_formats}")
            print(f"  Has AI response text: {has_text}")
            print(f"  Response type: {response_type}")
            
            if has_formats:
                formats = data["formats"]
                map_data = formats.get("map")
                graph_data = formats.get("graph")
                
                print(f"\n[FORMATS CONTENT]")
                print(f"  Map data: {'YES' if map_data else 'NO'}")
                if map_data:
                    print(f"    - Type: {map_data.get('type')}")
                    if map_data.get('type') == 'multiple_trajectories':
                        trajs = map_data.get('data', {}).get('trajectories', {})
                        if isinstance(trajs, dict):
                            print(f"    - Trajectories: {len(trajs)} floats")
                            first_fid = list(trajs.keys())[0] if trajs else None
                            if first_fid:
                                first_traj = trajs[first_fid]
                                has_correct_keys = 'float_id' in first_traj and 'points' in first_traj
                                points_count = len(first_traj.get('points', []))
                                print(f"    - Structure: {'CORRECT' if has_correct_keys else 'WRONG'}")
                                print(f"    - Points in first trajectory: {points_count}")
                
                print(f"  Graph data: {'YES' if graph_data else 'NO'}")
                if graph_data:
                    print(f"    - Type: {graph_data.get('type')}")
                    print(f"    - Has data: {bool(graph_data.get('data'))}")
                
                # Verdict
                if response_type in ["text", "map", "graph", "multi"]:
                    print(f"\n[VERDICT] PASS - Unified format confirmed")
                    results.append({"test": test['layer'], "status": "PASS"})
                else:
                    print(f"\n[VERDICT] FAIL - Invalid response_type")
                    results.append({"test": test['layer'], "status": "FAIL"})
            else:
                print(f"\n[VERDICT] FAIL - Missing 'formats' key")
                results.append({"test": test['layer'], "status": "FAIL"})
                
        else:
            print(f"\n[VERDICT] FAIL - HTTP {resp.status_code}")
            results.append({"test": test['layer'], "status": "FAIL"})
            
    except Exception as e:
        print(f"\n[VERDICT] ERROR - {str(e)[:100]}")
        results.append({"test": test['layer'], "status": "ERROR"})
    
    # Wait 60 seconds between queries to avoid rate limits (except after last query)
    if idx < len(test_cases) - 1:
        print(f"\n[Waiting 60 seconds to avoid rate limits...]")
        time.sleep(60)

# Final summary
print(f"\n{'='*70}")
print("FINAL SUMMARY")
print('='*70)

for result in results:
    status_symbol = "[OK]" if result['status'] == "PASS" else "[FAIL]"
    print(f"{status_symbol} {result['test']}: {result['status']}")

passed = sum(1 for r in results if r['status'] == "PASS")
total = len(results)

print(f"\n{'='*70}")
print(f"TOTAL: {passed}/{total} tests passed")
print('='*70)

if passed == total:
    print("\nALL LAYERS RETURNING UNIFIED FORMAT!")
else:
    print(f"\nWARNING: {total - passed} layer(s) not returning unified format")
