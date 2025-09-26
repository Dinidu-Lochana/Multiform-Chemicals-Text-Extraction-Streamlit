import re

def extract_order_confirmation(text):
    """Extract data from Order Confirmation (Format C)"""
    data = {}

    match = re.search(r"(\S+)\s+PO\s+(\d+)", text, re.IGNORECASE)
    if match:
        data["Order Number"] = match.group(1).strip()
        data["Purchase Order Number"] = match.group(2).strip()
    else:
        data["Order Number"] = None
        data["Purchase Order Number"] = None
    match = re.search(r"Customer\s+(?:Company\s*)?(.*?)(?:\n\s*\n|$)", text, re.DOTALL | re.IGNORECASE)
    data["Sold To"] = match.group(1).strip() if match else None
    data["Sold To Code"] = re.search(r"Code[:\s]+([\d/-]+)", text)
    data["Transport Mode"] = re.search(r"Mode of Transport[:\s]+(.+?)(?:\n|$)", text)   
    data["Incoterms"] = re.search(r"Incoterms[:\s]+(.+?)(?:\n|$)", text)
    match = re.search(r"Total Amount\s+([A-Z]{3})", text)
    data["Currency"] = match.group(1) if match else None
    data["Payment Terms"] = re.search(r"Payment Terms[:\s]+(.+?)(?:\n|$)", text)
    data["Product Code"] = re.search(r"Sales number[:\s]+(.+?)(?:\n|$)", text)
    match = re.search(r"Sales number[:\s].*?\n([\s\S]*?)\nIncoterms:", text, re.MULTILINE)
    data["Product Description"] = match.group(1).strip() if match else None
    match = re.search(r"Total net weight[:\s]+([\d,.]+)\s*KG", text, re.IGNORECASE)
    data["Net Weight (Kg)"] = match.group(1).replace(",", "") if match else None
    match = re.search(r"(\d+\.\d{4})", text)
    data['Price / Unit'] = match.group(1) if match else None
    if match:
        quantity = match.group(1).replace(",", "")
        # Remove trailing zeros after decimal point
        if '.' in quantity:
            quantity = quantity.rstrip('0').rstrip('.')
        data["Price / Unit"] = quantity
    else:
        data["Price / Unit"] = None
    match = re.search(r"(\d{1,3}(?:,\d{3})*\.\d{2})\b", text)
    data['Order Value'] = match.group(1) if match else None
    data["Total Value"] = re.search(r"Total Amount USD[:\s]+([\d,.]+)", text, re.IGNORECASE)
    
    match = re.search(r"BANK NAME:\s*\n([^\n]+)", text, re.IGNORECASE)
    data["Bank Name"] = match.group(1).strip() if match else None
    
    match = re.search(r"BANK NAME:[\s\S]*?\n[^\n]+\n([^\n]+)\n([^\n]+)\n([^\n]+)", text, re.IGNORECASE)
    if match:
        # Bank Address = line 1 + line 2
        data["Bank Address"] = match.group(1).strip() + " " + match.group(2).strip()
        # Bank City = line 3
        data["Bank City"] = match.group(3).strip()
    else:
        data["Bank Address"] = None
        data["Bank City"] = None
    match = re.search(r"(?:Contact[:\s]+|^)(Attn:\s*.*?)(?:\n|$)", text, re.IGNORECASE | re.MULTILINE)
    if match:
        data["Contact"] = re.sub(r"^Attn:\s*", "", match.group(1).strip(), flags=re.IGNORECASE)
    else:
        # Fallback: find line starting with "Attn:"
        match = re.search(r"^Attn:\s*(.*)$", text, re.MULTILINE | re.IGNORECASE)
        data["Contact"] = match.group(1).strip() if match else None
    # --- Email ---
    match = re.search(r"(?:Email[:\s]+)?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text, re.IGNORECASE)
    data["Email"] = match.group(1).strip() if match else None
    # --- Cell Phone ---
    data["Cell Phone"] = (
        re.search(r"Cell Phone[:\s]+(.+?)(?:\n|$)", text) or 
        re.search(r"(\+?\d{4}\s?\d{9}|\d{4}\s?\d{9})", text)
    )

    return data