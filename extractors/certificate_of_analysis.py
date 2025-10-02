import re

def extract_coa(text):
    """Extract data from COA (Format E)"""
    data = {}

    # Extract Product Code and Product Description
    match = re.search(r"Certificate of Analysis\s+([A-Z0-9-]+)\s+([^\n]+?)\s+Order Information", text, re.IGNORECASE | re.DOTALL)
    if match:
        data["Product Code"] = match.group(1).strip()
        data["Product Description"] = match.group(2).strip()
    else:
        data["Product Code"] = None
        data["Product Description"] = None
        
    # Extract Order Number and Purchase Order Number from Customer Reference
    cust_ref_match = re.search(r"Customer Reference\s+([A-Z0-9]+(?:-[A-Z0-9]+)*)\s*-?\s*PO\s*(\d+)", text, re.IGNORECASE)
    if cust_ref_match:
        data["Order Number"] = cust_ref_match.group(1).strip()
        data["Purchase Order Number"] = cust_ref_match.group(2).strip()
    else:
        data["Order Number"] = None
        data["Purchase Order Number"] = None

    data["Material Number"] = re.search(r"Material number\s*=\s*(\d+)", text)
    data["Specification Number"] = re.search(r"Specification number\s*=\s*(\d+)", text)
    data["Net Weight (Kg)"] = re.search(r"Quantity\s*([\d,]+\.\d+)\s*KG", text, re.IGNORECASE)
    # Convert match to string if found
    if isinstance(data["Net Weight (Kg)"], re.Match):
        data["Net Weight (Kg)"] = data["Net Weight (Kg)"].group(1).strip()

    return data