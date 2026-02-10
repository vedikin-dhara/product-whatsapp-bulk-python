import re

def validate_number(number):
    """
    Validates if the number starts with 91 or 1 and contains only digits.
    Returns purified number string if valid, else None.
    """
    s = str(number).strip().replace("+", "").replace(" ", "").replace("-", "")
    
    if not s.isdigit():
        return None
        
    if s.startswith("91") and len(s) >= 10:
        return s
    elif s.startswith("1") and len(s) >= 10:
        return s
    
    return None
