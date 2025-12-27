import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def wait_for_server():
    print(f"{BLUE}Waiting for backend to be ready...{RESET}")
    max_retries = 20
    for i in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=10)
            if resp.status_code == 200:
                print(f"{GREEN}Server is UP and HEALTHY!{RESET}")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
        print(f"Waiting... ({i+1}/{max_retries})")
    print(f"{RED}Server failed to come online.{RESET}")
    return False

def test_query(description, query_text):
    print(f"\n{YELLOW}--- Testing: {description} ---{RESET}")
    print(f"Query: '{query_text}'")
    
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/query", json={"query": query_text}, timeout=45)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            source = data.get("processing_source", "unknown")
            intent = data.get("intent", "unknown")
            
            print(f"Status: {GREEN}200 OK{RESET} | Time: {duration:.2f}s | Source: {BLUE}{source}{RESET} | Intent: {intent}")
            
            # Validation logic
            if data.get("result", {}).get("error"):
                print(f"{RED}❌ INTERNAL LOGIC ERROR: {data['result']['error']}{RESET}")
            elif data.get("error"):
                 print(f"{RED}❌ API ERROR: {data['error']}{RESET}")
            else:
                data_points = 0
                if isinstance(data.get("data"), list):
                    data_points = len(data["data"])
                elif isinstance(data.get("result"), dict) and "data" in data["result"]:
                     if isinstance(data["result"]["data"], list):
                        data_points = len(data["result"]["data"])
                
                # Check for Viz
                viz_kind = "None"
                if "viz" in data:
                    viz_kind = data["viz"].get("kind")
                elif "result" in data and "viz" in data["result"]:
                    viz_kind = data["result"]["viz"].get("kind")

                print(f"[DATA] Points: {data_points} | Visualization: {viz_kind}")
                if "text_response" in data:
                     print(f"[TEXT] Reply: {data['text_response'][:100]}...")
                elif "result" in data and "text_response" in data["result"]:
                     print(f"[TEXT] Reply: {data['result']['text_response'][:100]}...")
                     
        else:
            print(f"[FAIL] Status {response.status_code}")
            print(response.text[:200])
            
    except Exception as e:
        print(f"[ERROR] EXCEPTION: {e}")

def get_valid_floats():
    try:
        print(f"\n{BLUE}Fetching valid float IDs...{RESET}")
        resp = requests.get(f"{BASE_URL}/floats?limit=5")
        if resp.status_code == 200:
            data = resp.json()
            floats = [f['platform_number'] for f in data.get('floats', [])]
            print(f"Found floats: {floats}")
            return floats
        return []
    except:
        return []

def main():
    if not wait_for_server():
        sys.exit(1)
        
    valid_ids = get_valid_floats()
    fid1 = valid_ids[0] if len(valid_ids) > 0 else 2902296
    fid2 = valid_ids[1] if len(valid_ids) > 1 else 2902297

    print(f"\n{BLUE}=== STARTING COMPREHENSIVE BACKEND TEST ==={RESET}")

    # 1. Conversational (Layer 1)
    test_query("Greeting", "Hello there!")
    test_query("Capabilities", "What can this system do?")

    # 2. Simple Data Retrieval (Layer 1)
    test_query("List Floats", "Show me all floats")
    test_query("Region Query", "Floats in Arabian Sea")
    
    # 3. Single Float Specifics (Layer 1)
    test_query("Float Profile", f"Show me temperature profile for float {fid1}")
    test_query("Float Trajectory", f"Where did float {fid1} go?")
    
    # 4. Complex Orchestration (Layer 2)
    test_query("Multi-Float Trajectory", "Show me trajectories for all floats in Indian Ocean")
    test_query("Comparison", f"Compare temperature of floats {fid1} and {fid2}")
    
    # 5. Fallback/Analysis (Layer 3)
    test_query("Analytical Question", "Which float typically has the warmest temperature?")
    
    # 6. Negative Tests
    test_query("Invalid Float ID", "Show me details for float 999999999")
    test_query("Nonsense Query", "What is the capital of Mars?")

    print(f"\n{BLUE}=== TEST COMPLETE ==={RESET}")

if __name__ == "__main__":
    main()
