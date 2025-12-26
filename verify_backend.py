import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_query(query_text, description):
    print(f"\n--- Testing: {description} ---")
    print(f"Query: '{query_text}'")
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/query", json={"query": query_text}, timeout=30)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: 200 OK (Time: {duration:.2f}s)")
            print("Keys in response:", list(data.keys()))
            
            # Verify Fast Formatter structure
            required_keys = ["viz", "data", "text", "suggestions"]
            missing_keys = [k for k in required_keys if k not in data]
            
            if missing_keys:
                print(f"❌ FAILED: Missing keys: {missing_keys}")
            else:
                print("✅ Structure Valid")
                
            # Check specific data types
            if isinstance(data.get("data"), list):
                print(f"✅ 'data' is a list (Length: {len(data['data'])})")
            else:
                print(f"❌ 'data' is NOT a list: {type(data.get('data'))}")
                
            if data.get("viz"):
                print(f"✅ Visualization type: {data['viz'].get('type')}")
            else:
                print("ℹ️ No visualization returned")
                
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    # Wait for server to start
    print("Waiting for server to be ready...")
    time.sleep(5) 
    
    # 1. General Text Query
    test_query("What is this bot?", "General Text Query")
    
    # 2. Single Float Query
    test_query("Show me float 5906504", "Single Float Query")
    
    # 3. Region Query (Many Floats)
    test_query("floats in arabian sea", "Region Query (Many Floats)")
    
    # 4. Trajectory Query (Many Floats - Optimized path)
    test_query("show trajectories for floats in arabian sea", "Trajectory Query (Bulk)")

if __name__ == "__main__":
    main()
