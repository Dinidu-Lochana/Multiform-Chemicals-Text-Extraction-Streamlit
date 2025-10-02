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

    # Extract Order number and Purchase Order number
    match = re.search(r"(\S+?)\s*\.?\s*PO\s+(\d+)", text, re.IGNORECASE)
    if match:
        order_num = match.group(1).strip()
        # Remove trailing hyphen or period if present
        order_num = order_num.rstrip('-.') 
        data["Order Number"] = order_num
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

    # Find "Sales number" line
    match = re.search(r"Sales number:.*", text)
    if match:
        # Get all lines
        lines = text.splitlines()
        idx = lines.index(match.group(0))
        # Find next non-empty line after sales number
        for i in range(idx + 1, len(lines)):
            if lines[i].strip():
                data["Product Description"] = lines[i].strip()
                break
    
    for h in headers_none:
        data.pop(h, None)

    # Bank Details
    # Bank details
    bank_name_match = re.search(r"BANK NAME:\s*\n([^\n]+)", text, re.IGNORECASE)

    if bank_name_match:
        data["Bank Name"] = bank_name_match.group(1).strip()
        
        address_match = re.search(r"BANK NAME:[\s\S]*?\n[^\n]+\n([^\n]+)\n([^\n]+)\n([^\n]+)", text, re.IGNORECASE)
        if address_match:
            data["Bank Address"] = address_match.group(1).strip() + " " + address_match.group(2).strip()
            data["Bank City"] = address_match.group(3).strip()
        else:
            data["Bank Address"] = None
            data["Bank City"] = None
    else:
        # Look for unlabeled bank details
        # Find line with "Bank" (word boundary to ensure it's a complete word)
        bank_section = re.search(
            r"\b([A-Z][^\n]*Bank)\s*\n"  # Bank name - must start with capital letter, end with "Bank"
            r"([^\n]+)\s*\n"              # Line 1: Trade Operations Dept.
            r"([^\n]+)\s*\n"              # Line 2: No 65C, Dharmapala Mawatha,
            r"([^\n]+)\s*\n"              # Line 3: Colombo 7
            r"([^\n]+)",                  # Line 4: Sri Lanka
            text,
            re.IGNORECASE
        )
        
        if bank_section:
            data["Bank Name"] = bank_section.group(1).strip()
            # Address = Line 1 + Line 2
            data["Bank Address"] = bank_section.group(2).strip() + " " + bank_section.group(3).strip()
            # City = Line 3 (Colombo 7)
            data["Bank City"] = bank_section.group(4).strip()
        else:
            data["Bank Name"] = None
            data["Bank Address"] = None
            data["Bank City"] = None

    # Contact
    contact_match = re.search(r"(?:Contact:|Attn:)\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    data["Contact"] = contact_match.group(1).strip() if contact_match else None

    if data["Contact"]:
        data["Contact"] = re.sub(r"^Attn:\s*", "", data["Contact"], flags=re.IGNORECASE)

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

    match = re.search(r"Amount\s*\n\s*([A-Z]{3})\b", text)
    data["Currency"] = match.group(1) if match else None

    data["Order Value"] = re.search(r"Sub Total\s*([\d,.]+)", text)
    data["Total Value"] = re.search(r"Total Amount\s*USD\s*([\d,.]+)", text)
    
    transport_match = re.search(r"Mode of transport[:\s]*(.+?)(?=\s*\n|$)", text, re.IGNORECASE)
    if transport_match:
        transport_value = transport_match.group(1).strip()
        # Only assign if there's actual content (not just whitespace)
        if transport_value and not transport_value.startswith(("Import", "NÂ°", "N°")):
            data["Transport Mode"] = transport_value
        else:
            data["Transport Mode"] = None


    data["Material Number"] = re.search(r"Material numbers.*?=\s*(\d+)", text)
    data["Specification Number"] = re.search(r"Specification number.*?=\s*(\d+)", text)

    return data