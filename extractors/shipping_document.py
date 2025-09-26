import re

def extract_packing_list(text):
    """Extract data from Packing List Shipping Docs (Format B)"""
    data = {}
    match = re.search(r"Customer\s+(?:Company\s*)?(.*?)(?:\n\s*\n|$)", text, re.DOTALL | re.IGNORECASE)
    data["Sold To"] = match.group(1).strip() if match else None
    
    data["Sold To Code"] = re.search(r"Code[:\s]+(.+?)(?:\n|$)", text)
    data["Incoterms"] = re.search(r"Incoterms[:\s]+(.+?)(?:\n|$)", text)
    data["Payment Terms"] = re.search(r"Payment\s*terms[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    
    match = re.search(r"(\d+\s*/\s*\d+\s*/\s*\d+)", text)
    data["O/Order number"] = match.group(1) if match else None
    # Extract Shipment Date (comes after the O/Order pattern)
    date_match = re.search(r"(\d+\s*/\s*\d+\s*/\s*\d+)\s+(\d+\s+\w+\s+\d+)", text)
    data["Shipment Date"] = date_match.group(2) if date_match else None
    # Extract Y/Order number (comes after the date)
    match = re.search(r"(\S+)\s+PO\s+(\d+)", text, re.IGNORECASE)
    if match:
        data["Order Number"] = match.group(1).strip()
        data["Purchase Order Number"] = match.group(2).strip()
    else:
        data["Order Number"] = None
        data["Purchase Order Number"] = None
    # Extract Net Weight (Kg) (number + unit like KG)
    net_qty_match = re.search(r"(\d+\.?\d*\s+[A-Z]+)", text)
    data["Order Net quantity"] = net_qty_match.group(1).strip() if net_qty_match else None
    # Extract the three values from the line after Y/Order number
    # Pattern to match: number + KG, then price, then amount
    pattern = r"(\d+(?:\.\d+)?\s*KG)\s+(\d+(?:\.\d+)?)\s+([\d,]+\.?\d*)"
    match = re.search(pattern, text)
    if match:
        data["Order Net quantity"] = match.group(1)       
        data["Price / Unit"] = match.group(2)       
        data["Amount"] = match.group(3) 
    if match:
        quantity = match.group(2).replace(",", "")
        # Remove trailing zeros after decimal point
        if '.' in quantity:
            quantity = quantity.rstrip('0').rstrip('.')
        data["Price / Unit"] = quantity
    else:
        data["Price / Unit"] = None   
    data["Product Code"] = re.search(r"Sales number[:\s]+([A-Z0-9-]+)", text)
    headers_none = ["O/Order number","Shipment Date","Order Net quantity","Amount"]
    
    for h in headers_none:
        data.pop(h, None)
    # Bank Details
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
    # Contact
    contact_match = re.search(r"(?:Contact:|Attn:)\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    data["Contact"] = contact_match.group(1).strip() if contact_match else None
    # Email
    email_match = re.search(r"([\w\.-]+@[\w\.-]+\.\w+)", text)
    data["Email"] = email_match.group(1).strip() if email_match else None
    # Cell Phone
    cell_match = re.search(
        r"(?:Cell Phone[:\s]*|(?<=\n))(\+?\d[\d\s]{10,}\d)", 
        text, 
        re.MULTILINE
    )
    data["Cell Phone"] = cell_match.group(1).strip() if cell_match else None
    match = re.search(r"Total net weight:\s*([\d,.]+)\s*KG", text, re.IGNORECASE)
    if match:
        quantity = match.group(1).replace(",", "")
        # Remove trailing zeros after decimal point
        if '.' in quantity:
            quantity = quantity.rstrip('0').rstrip('.')
        data["Net Weight (Kg)"] = quantity
    else:
        data["Net Weight (Kg)"] = None
    data["Order Value"] = re.search(r"Sub Total\s*([\d,.]+)", text)
    data["Total Value"] = re.search(r"Total Amount\s*USD\s*([\d,.]+)", text)
    
    data["Transport Mode"] = re.search(r"Mode of transport[:\s]+(.*?)(?=\s+Import licence|$)", text)
    data["Material Number"] = re.search(r"Material numbers.*?=\s*(\d+)", text)
    data["Specification Number"] = re.search(r"Specification number.*?=\s*(\d+)", text)

    return data