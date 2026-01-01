import requests
import json

URL = "http://127.0.0.1:8000/query"
query = "average temperature at 100m depth of float 2900565"

print(f"Testing: '{query}'")
print("="*70)

resp = requests.post(URL, json={"query": query, "session_id": "debug_layer3"}, timeout=60)

if resp.status_code == 200:
    data = resp.json()
    
    print(f"\n[RESPONSE STRUCTURE]")
    print(f"Processing Source: {data.get('processing_source')}")
    print(f"Response Type: {data.get('response_type')}")
    print(f"AI Response: {data.get('ai_synthesized_response')[:200] if data.get('ai_synthesized_response') else 'None'}")
    
    print(f"\n[RAW RESULT]")
    result = data.get('result', {})
    print(f"Result Keys: {list(result.keys())}")
    
    if 'SQL' in result:
        print(f"SQL: {result.get('SQL')}")
    if 'TEXT' in result:
        print(f"TEXT: {result.get('TEXT')[:200] if result.get('TEXT') else 'Empty'}")
    if 'GRAPHS' in result:
        print(f"GRAPHS: {result.get('GRAPHS')}")
    if 'success' in result:
        print(f"Success: {result.get('success')}")
    
    print(f"\n[FORMATS]")
    formats = data.get('formats', {})
    print(f"Has map: {formats.get('map') is not None}")
    print(f"Has graph: {formats.get('graph') is not None}")
    
    print(f"\n{'='*70}")
    print(f"Full response (truncated):")
    print(json.dumps(data, indent=2)[:1000])
else:
    print(f"Error: {resp.status_code}")
