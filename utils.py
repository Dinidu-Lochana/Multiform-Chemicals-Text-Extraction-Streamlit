import re

def convert_regex_results_to_strings(data):
    """
    Convert regex Match objects to strings and clean up data
    """
    for k, v in data.items():
        if isinstance(v, re.Match):
            # group(1) if available, else fallback to whole match
            try:
                data[k] = v.group(1).strip()
            except IndexError:
                data[k] = v.group(0).strip()
        elif isinstance(v, str):
            data[k] = v.strip()
        else:
            data[k] = None
    
    return data