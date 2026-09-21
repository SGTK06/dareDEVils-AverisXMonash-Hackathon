"""Product/Item feature, unit, and dimension extraction and comparison."""

import re
import math
from typing import Dict, List, Set, Tuple, Any

# Matches a number (integer or decimal) followed by an optional unit.
NUMBER_UNIT_REGEX = re.compile(
    r'(?P<number>\d+(?:[.,]\d+)?)\s*(?P<unit>mm|cm|m|ft|feet|in|inch|inches|kg|kgs|g|lb|lbs|ton|tons|cbm|m3|pieces|pcs|sets?)?',
    re.IGNORECASE
)

KNOWN_FEATURES = {
    'ivory', 'black', 'white', 'coated', 'wooden', 'steel', 'aluminium', 'aluminum', 
    'red', 'blue', 'long', 'a4', 'a3', 'copier', 'inkjet', 'digital', 'uncoated', 'woodfree'
}

def _tokens(text: str) -> List[str]:
    """Extract lowercase alphanumeric tokens."""
    return re.findall(r'[a-z0-9]+', str(text).lower())

def _unit_value(number_str: str, unit_str: str) -> Tuple[float, str]:
    """Normalize a number and unit to a standard base (e.g. feet to meters)."""
    factors = {
        'mm': 0.001, 'cm': 0.01, 'm': 1.0, 
        'ft': 0.3048, 'feet': 0.3048, 'in': 0.0254, 'inch': 0.0254, 'inches': 0.0254,
        'kg': 1.0, 'kgs': 1.0, 'g': 0.001, 'lb': 0.453592, 'lbs': 0.453592, 'ton': 1000.0, 'tons': 1000.0,
        'cbm': 1.0, 'm3': 1.0
    }
    num = float(number_str.replace(',', ''))
    unit = (unit_str or '').lower()
    
    # Map to standardized units
    standard_unit = unit
    if unit in {'mm', 'cm', 'm', 'ft', 'feet', 'in', 'inch', 'inches'}:
        standard_unit = 'm'
    elif unit in {'kg', 'kgs', 'g', 'lb', 'lbs', 'ton', 'tons'}:
        standard_unit = 'kg'
    elif unit in {'cbm', 'm3'}:
        standard_unit = 'cbm'
    elif not unit:
        standard_unit = 'unitless'
        
    return num * factors.get(unit, 1.0), standard_unit

def item_signature(text: str) -> Dict[str, Any]:
    """Extract numerical dimensions and product features from an item description."""
    nums = []
    for match in NUMBER_UNIT_REGEX.finditer(str(text)):
        value, unit = _unit_value(match.group('number'), match.group('unit'))
        nums.append((round(value, 6), unit))
    
    words = set(_tokens(text))
    features = sorted(words & KNOWN_FEATURES)
    return {'numbers': nums, 'features': features}

def _cosine_similarity(left_text: str, right_text: str) -> float:
    """Calculate cosine similarity between two strings using standard Python."""
    left_tokens = _tokens(left_text)
    right_tokens = _tokens(right_text)
    
    vocab = set(left_tokens + right_tokens)
    if not vocab:
        return 0.0
        
    left_vec = [left_tokens.count(w) for w in vocab]
    right_vec = [right_tokens.count(w) for w in vocab]
    
    dot_product = sum(l * r for l, r in zip(left_vec, right_vec))
    mag_left = math.sqrt(sum(l * l for l in left_vec))
    mag_right = math.sqrt(sum(r * r for r in right_vec))
    
    if mag_left == 0 or mag_right == 0:
        return 0.0
    return dot_product / (mag_left * mag_right)

def compare_items(si_items: List[str], bl_items: List[str], threshold: float = 0.35) -> List[Dict[str, Any]]:
    """Compare items between SI and BL, matching them and comparing their signatures."""
    if not si_items and not bl_items:
        return []
        
    pairs = []
    used_bl_indices = set()
    
    # Clean empty items
    si_items = [str(x).strip() for x in si_items if str(x).strip()]
    bl_items = [str(x).strip() for x in bl_items if str(x).strip()]

    for i, si_item in enumerate(si_items):
        # Find best match in BL items
        best_score = -1.0
        best_idx = -1
        
        for j, bl_item in enumerate(bl_items):
            if j in used_bl_indices:
                continue
            score = _cosine_similarity(si_item, bl_item)
            if score > best_score:
                best_score = score
                best_idx = j
                
        if best_idx == -1 or best_score < threshold:
            pairs.append({
                'si': si_item, 
                'bl': None, 
                'cosine': round(best_score, 3) if best_score != -1 else 0.0,
                'verdict': 'MISMATCH', 
                'reason': 'No similar item found in BL'
            })
            continue
            
        used_bl_indices.add(best_idx)
        bl_item = bl_items[best_idx]
        
        # Compare signatures
        si_sig = item_signature(si_item)
        bl_sig = item_signature(bl_item)
        
        reasons = []
        if si_sig['features'] != bl_sig['features']:
            reasons.append('product features differ')
        
        si_nums = sorted(si_sig['numbers'])
        bl_nums = sorted(bl_sig['numbers'])
        if si_nums != bl_nums:
            reasons.append('quantities/dimensions/units differ')
            
        verdict = 'MATCH'
        if reasons:
            verdict = 'MISMATCH'
            
        pairs.append({
            'si': si_item,
            'bl': bl_item,
            'cosine': round(best_score, 3),
            'verdict': verdict,
            'reason': '; '.join(reasons)
        })
        
    for j, bl_item in enumerate(bl_items):
        if j not in used_bl_indices:
            pairs.append({
                'si': None,
                'bl': bl_item,
                'cosine': 0.0,
                'verdict': 'MISMATCH',
                'reason': 'Item missing from SI'
            })
            
    return pairs
