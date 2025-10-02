import re

def extract_packing_list_f(text):
    """Extract data from Packing List (Format F)"""
    data = {}

    match = re.search(r"Customer Ref\.\s*:\s*([A-Z0-9]+(?:-[A-Z0-9]+)*)\s*-?\s*PO\s+(\d+)", text, re.IGNORECASE)
    if match:
        data["Order Number"] = match.group(1).strip()
        data["Purchase Order Number"] = match.group(2).strip()
    else:
        data["Order Number"] = None
        data["Purchase Order Number"] = None
    
    # Consignee block
    data["Sold To Code"] = re.search(r"Consignee:\s*Code:\s*(\d+)", text)
    data["Sold To"] = re.search(r"Consignee:.*?Company\s*(.+?)\s*Customer Ref\.", text, re.DOTALL) 
    data["Incoterms"] = re.search(r"Incoterms[:\s]+(.+?)(?:\n|$)", text)
    data["Transport Mode"] = re.search(r"Mode of transport[:\s]+(.*?)(?=\s+Import licence|$)", text)
    
    match = re.search(r"(?:Total:\s*\d+\s*Packages\s+|Sales number:.*?\s[\d,]+\.\d{3}\s*KG\s+)([\d,]+\.\d{3})", text)
    if match:
        quantity = match.group(1).replace(",", "")
        # Remove trailing zeros after decimal point
        if '.' in quantity:
            quantity = quantity.rstrip('0').rstrip('.')
        data["Net Weight (Kg)"] = quantity
    else:
        data["Net Weight (Kg)"] = None

    return data