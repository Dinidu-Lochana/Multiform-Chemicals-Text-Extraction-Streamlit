import re

def extract_purchase_order(text):
    """Extract data from Purchase Order Terms & Conditions (Format A)"""
    data = {}

    data["Purchase Order Number"] = re.search(r"Purchase order\s*:\s*(\S+)", text)
    data["Sold To"] = re.search(r"Invoice To:\s*(.*?)(?:\n\s*\n|$)", text, re.DOTALL)    
    
    data["Currency"] = re.search(r"Currency[:\s]+(\S+)", text)
    
    data["Payment Terms"] = re.search(r"Terms of Payment\s*:\s*([^\n_]+)", text)
    
    # Item number
    item = re.search(r"^(\d+)\s", text, re.MULTILINE)
    if item:
        data["Item"] = item.group(1)
    # Material Number
    mat_no = re.search(r"^\s*\d+\s+(\d+)", text, re.MULTILINE)
    if mat_no:
        data["Material Number"] = mat_no.group(1)
    # Quantity and Unit
    qty_unit = re.search(r"([\d,]+\.\d+)\s*(kg|g|l|ml)", text, re.IGNORECASE)
    if qty_unit:
        quantity = qty_unit.group(1).replace(",", "")
        # Remove trailing zeros after decimal point
        if '.' in quantity:
            quantity = quantity.rstrip('0').rstrip('.')
        data["Net Weight (Kg)"] = quantity
        data["Unit"] = qty_unit.group(2)
     
    # Price/Unit and Net Value
    price_val = re.search(r"(\d+\.\d{2})\s+(\d+,\d+\.\d{2})", text)
    if price_val:
        data["Price / Unit"] = price_val.group(1)
        data["Order Value"] = price_val.group(2)
    data["Total Value"] = re.search(r"Total net value excl\. tax\s+([\d,]+\.\d{2})", text)
    
    # Description (between Material No. and Price columns)
    match = re.search(r"\b\d+\s+\d+\s+(.+?)\s+(GIV(?:AUDAN)?)\s+(.+?)(?=\s*$)", text, re.IGNORECASE | re.MULTILINE)
    if match:
        data["Product Description"] = match.group(1).strip()
        data["Product Code"] = match.group(3).strip()

    data["PO against Contract"] = re.search(r"PO against Contract[:\s]+(.+?)(?:\n|$)", text)
    match = re.search(r"As per\s+[Ss]pecification number[:\s]+(\d+)", text)
    data["Specification Number"] = match.group(1).strip() if match else None
    headers_none = ["Unit","Item","PO against Contract"]
    
    for h in headers_none:
        data.pop(h, None)
    
    return data