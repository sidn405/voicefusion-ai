"""
Cold Call Trigger Script
Makes outbound sales calls to prospects using the LawBot 360 Voice Bot
"""

import requests
import json
import csv
from typing import List, Dict
import time

# Your server URL
SERVER_URL = "https://voicefusion-ai-production.up.railway.app"

def make_single_cold_call(to_number: str, prospect_name: str = "", firm_name: str = "") -> Dict:
    """
    Make a single cold call to a prospect
    
    Args:
        to_number: Phone number in E.164 format (+15551234567)
        prospect_name: Name of the person (optional)
        firm_name: Name of their law firm (optional)
    
    Returns:
        dict: Response from server with call_sid and status
    """
    url = f"{SERVER_URL}/api/make-cold-call"
    
    payload = {
        "to_number": to_number,
        "prospect_name": prospect_name,
        "firm_name": firm_name
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if result.get("status") == "success":
            print(f"✅ Call initiated to {prospect_name or to_number}")
            print(f"   Call SID: {result.get('call_sid')}")
        else:
            print(f"❌ Failed: {result.get('message')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error calling {to_number}: {e}")
        return {"status": "error", "message": str(e)}


def make_batch_cold_calls(prospects: List[Dict], delay_seconds: int = 60) -> List[Dict]:
    """
    Make multiple cold calls with delay between each
    
    Args:
        prospects: List of dicts with keys: to_number, prospect_name, firm_name
        delay_seconds: Seconds to wait between calls (default 60)
    
    Returns:
        List of results for each call
    """
    results = []
    
    for i, prospect in enumerate(prospects):
        print(f"\n📞 Calling {i+1}/{len(prospects)}: {prospect.get('prospect_name', 'Unknown')}")
        
        result = make_single_cold_call(
            to_number=prospect.get("to_number"),
            prospect_name=prospect.get("prospect_name", ""),
            firm_name=prospect.get("firm_name", "")
        )
        
        results.append({
            "prospect": prospect,
            "result": result,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Wait before next call (unless it's the last one)
        if i < len(prospects) - 1:
            print(f"⏳ Waiting {delay_seconds} seconds before next call...")
            time.sleep(delay_seconds)
    
    return results


def load_prospects_from_csv(csv_file: str) -> List[Dict]:
    """
    Load prospects from CSV file
    
    CSV format:
    to_number,prospect_name,firm_name
    +15043833692,Jessica D. Alexander,Cozen O'Connor
    +15044853763,John Smith,Smith & Associates
    
    Args:
        csv_file: Path to CSV file
    
    Returns:
        List of prospect dictionaries
    """
    prospects = []
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prospects.append({
                "to_number": row.get("to_number", "").strip(),
                "prospect_name": row.get("prospect_name", "").strip(),
                "firm_name": row.get("firm_name", "").strip()
            })
    
    return prospects


def save_results_to_csv(results: List[Dict], output_file: str = "call_results.csv"):
    """Save call results to CSV for tracking"""
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['timestamp', 'to_number', 'prospect_name', 'firm_name', 
                     'status', 'call_sid', 'message']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            prospect = result['prospect']
            call_result = result['result']
            
            writer.writerow({
                'timestamp': result['timestamp'],
                'to_number': prospect.get('to_number'),
                'prospect_name': prospect.get('prospect_name'),
                'firm_name': prospect.get('firm_name'),
                'status': call_result.get('status'),
                'call_sid': call_result.get('call_sid', ''),
                'message': call_result.get('message', '')
            })
    
    print(f"\n✅ Results saved to {output_file}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    
    # OPTION 1: Make a single call
    print("=" * 70)
    print("OPTION 1: Single Cold Call")
    print("=" * 70)
    
    result = make_single_cold_call(
        to_number="+15043833692",
        prospect_name="Jessica D. Alexander",
        firm_name="Cozen O'Connor"
    )
    
    # OPTION 2: Make multiple calls from a list
    print("\n" + "=" * 70)
    print("OPTION 2: Batch Cold Calls")
    print("=" * 70)
    
    prospects = [
        {
            "to_number": "+15043833692",
            "prospect_name": "Jessica D. Alexander",
            "firm_name": "Cozen O'Connor"
        },
        {
            "to_number": "+15044853793",
            "prospect_name": "John Smith",
            "firm_name": "Smith & Associates"
        },
        {
            "to_number": "+12255727537",
            "prospect_name": "Sarah Johnson",
            "firm_name": "Johnson Legal Group"
        }
    ]
    
    # Uncomment to run batch calls
    # results = make_batch_cold_calls(prospects, delay_seconds=60)
    # save_results_to_csv(results)
    
    # OPTION 3: Load from CSV and call
    print("\n" + "=" * 70)
    print("OPTION 3: Load from CSV and Call")
    print("=" * 70)
    
    # Uncomment to load from CSV
    # prospects = load_prospects_from_csv("prospects.csv")
    # results = make_batch_cold_calls(prospects, delay_seconds=60)
    # save_results_to_csv(results)
    
    print("\n✅ Done!")