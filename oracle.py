# core/oracle.py
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple

def fetch_oracle_outcome(market_oracle_url: str, metric_def: str) -> Optional[Tuple[bool, str]]:
    """
    Fetch outcome from oracle URL and parse according to metric_def.
    
    Returns: (outcome_yes: bool, explanation: str) or None if failed.
    """
    try:
        # Step 1: Fetch page content
        response = requests.get(market_oracle_url, timeout=10)
        response.raise_for_status()
        
        # Step 2: Simple parsing - look for numbers in metric_def context
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        # Step 3: Extract key number from metric_def (e.g. "20,000,000" from "≥ 20,000,000")
        threshold_match = re.search(r'[\$€]?([\d,]+\.?\d*)', metric_def)
        if not threshold_match:
            return None, "Could not parse threshold from metric definition"
        
        threshold_str = threshold_match.group(1).replace(',', '')
        threshold = float(threshold_str)
        
        # Step 4: Find numbers in page text, take largest (common pattern for dashboards)
        numbers = [float(n.replace(',', '')) for n in re.findall(r'[\d,]+\.?\d+', text) if float(n.replace(',', '')) > 1000]
        if not numbers:
            return None, "No numeric data found on oracle page"
        
        actual_value = max(numbers)  # Simplest: take biggest number (revenue, users, etc.)
        
        # Step 5: Compare to threshold (assumes "≥ threshold = YES")
        outcome_yes = actual_value >= threshold
        explanation = f"Found value {actual_value:,} vs threshold {threshold:,} → {'YES' if outcome_yes else 'NO'}"
        
        return outcome_yes, explanation
        
    except Exception as e:
        return None, f"Failed to fetch/parse oracle: {str(e)}"
