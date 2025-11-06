from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Optional

import httpx


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "patches"


def normalize_champ_name(name: str) -> str:
    """Normalize champion name for matching (lowercase, handle special cases)."""
    name = name.lower().strip()
    name = name.replace("'", "").replace(" ", "")
    # Handle Wukong as MonkeyKing
    if name == "wukong":
        name = "monkeyking"
    return name


def fetch_winrates_metasrc(client: httpx.Client) -> Optional[Dict[str, float]]:
    """
    Fetch ARAM win rates from metasrc.com/lol/aram/stats
    Returns dict mapping normalized champion name -> win rate (0.0 to 1.0)
    """
    url = "https://www.metasrc.com/lol/aram/stats"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        resp = client.get(url, headers=headers, timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            print(f"metasrc.com returned status {resp.status_code}")
            return None
        
        html = resp.text
        winrates: Dict[str, float] = {}
        
        # Parse HTML table structure
        tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.DOTALL | re.IGNORECASE)
        table_content = tbody_match.group(1) if tbody_match else html
        
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL | re.IGNORECASE)
        
        for row in rows:
            # Extract champion name from link or span
            name_patterns = [
                r'<a[^>]*href="[^"]*aram/build/[^"]*"[^>]*>([A-Z][a-zA-Z\']+)</a>',
                r'<span[^>]*hidden[^>]*>([A-Z][a-zA-Z\']+)</span>',
            ]
            
            champ_name = None
            for name_pat in name_patterns:
                name_match = re.search(name_pat, row, re.IGNORECASE)
                if name_match:
                    champ_name = name_match.group(1).strip()
                    break
            
            if not champ_name:
                continue
            
            # Extract win rate percentage (filter for reasonable ARAM range 35-65%)
            wr_matches = list(re.finditer(r'([0-9]{1,2}\.[0-9]+)%', row))
            for wr_match in wr_matches:
                try:
                    wr_value = float(wr_match.group(1)) / 100.0
                    if 0.35 <= wr_value <= 0.65:
                        normalized = normalize_champ_name(champ_name)
                        winrates[normalized] = wr_value
                        break
                except ValueError:
                    continue
        
        if winrates:
            print(f"Fetched {len(winrates)} win rates from metasrc.com")
            return winrates
        
        print("Could not extract win rates from metasrc.com")
        return None
        
    except Exception as e:
        print(f"Error fetching from metasrc.com: {e}")
        return None


def load_winrates(champs: list[str], patch: str | None = None, verbose: bool = True) -> dict[str, float]:
    """
    Load ARAM win rates from metasrc.com
    Returns dict mapping normalized champion name -> win rate (0.0 to 1.0)
    
    Args:
        champs: List of champion names to fetch win rates for
        patch: Optional patch string (not used, kept for compatibility)
        verbose: Whether to print progress messages (default True)
    """
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        if verbose:
            print("Fetching win rates from metasrc.com...")
        
        all_winrates = fetch_winrates_metasrc(client)
        
        if not all_winrates:
            if verbose:
                print("Warning: Could not fetch win rates, using defaults")
            return {normalize_champ_name(c): 0.5 for c in champs}
        
        # Map to requested champions
        result: dict[str, float] = {}
        for champ in champs:
            normalized = normalize_champ_name(champ)
            wr = all_winrates.get(normalized, 0.5)  # Default to 0.5 if not found
            result[normalized] = wr
        
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch ARAM win rates from metasrc.com")
    parser.add_argument("--patch", help="Patch dir name like 15.20 or 14.99 (optional, for testing with champ list)")
    parser.add_argument("--test", action="store_true", help="Test with sample champions")
    args = parser.parse_args()
    
    # Test champions list
    test_champs = [
        "Ahri", "Akali", "Aatrox", "Ashe", "Blitzcrank", "Braum", "Caitlyn", 
        "Darius", "Ezreal", "Fizz", "Garen", "Jinx", "Lux", "Master Yi",
        "Malphite", "Nasus", "Pyke", "Rakan", "Sona", "Thresh", "Vayne",
        "Yasuo", "Zed", "Ziggs", "Zoe"
    ]
    
    if args.patch:
        # Load champions from patch data
        patch_dir = DATA_ROOT / args.patch
        champs_path = patch_dir / "champs.json"
        if champs_path.exists():
            champs_data = json.loads(champs_path.read_text(encoding="utf-8"))
            champs = [c.get("name") for c in champs_data if c.get("name")]
            print(f"Loaded {len(champs)} champions from {champs_path}")
        else:
            print(f"Patch data not found at {champs_path}, using test champions")
            champs = test_champs
    else:
        champs = test_champs
    
    print(f"\nFetching win rates for {len(champs)} champions...")
    winrates = load_winrates(champs, args.patch)
    
    print(f"\n=== Win Rates ({len(winrates)} champions) ===")
    sorted_items = sorted(winrates.items(), key=lambda x: x[1], reverse=True)
    for champ, wr in sorted_items[:30]:  # Show top 30
        print(f"{champ:20s} {wr*100:5.2f}%")
    
    # Save to JSON for inspection
    output = {
        "source": "metasrc.com",
        "champions": {k: round(v * 100, 2) for k, v in winrates.items()}
    }
    output_path = Path(__file__).parent / "winrates_test.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results to {output_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
