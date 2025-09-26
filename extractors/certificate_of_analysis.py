import re

def extract_coa(text):
    """Extract data from COA (Format E)"""
    data = {}

    # Extract Order Number and Purchase Order Number from Customer Reference
    cust_ref_match = re.search(r"Customer Reference\s+(\S+)-?\s*PO\s*(\d+)", text)
    if cust_ref_match:
        data["Order Number"] = cust_ref_match.group(1)  
        data["Purchase Order Number"] = cust_ref_match.group(2)  
    else:
        # Fallback: keep previous extraction logic if needed
        data["Order Number"] = None
        data["Purchase Order Number"] = None
    data["Material Number"] = re.search(r"Material number\s*=\s*(\d+)", text)
    data["Specification Number"] = re.search(r"Specification number\s*=\s*(\d+)", text)
    data["Net Weight (Kg)"] = re.search(r"Quantity\s*([\d,]+\.\d+)\s*KG", text, re.IGNORECASE)
    # Convert match to string if found
    if isinstance(data["Net Weight (Kg)"], re.Match):
        data["Net Weight (Kg)"] = data["Net Weight (Kg)"].group(1).strip()

    return data