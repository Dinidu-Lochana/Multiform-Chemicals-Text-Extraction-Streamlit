import re

def extract_proforma_invoice(text):
    """Extract data from PROFORMA INVOICE (Excel) (Format D)"""
    data = {}

    # Header details
    match = re.search(r"(\S+)\s+PO\s+(\d+)", text)
    if match:
        data["Order Number"] = match.group(1).strip()
        data["Purchase Order Number"] = match.group(2).strip()
    else:
        data["Order Number"] = None
        data["Purchase Order Number"] = None
    data["Order Type"] = re.search(r"Order Type:\s*(.+)\s+Customer Ref", text)
    
    # Sold To & Ship To
    data["Sold To"] = re.search(r"Sold To:\s*(.+?)(?=\s+Transport Mode:)", text, re.S)
    
    data["Sold To Code"] = re.search(r"Sold To Code\s+(\d+)", text)
    
    # Transport / Delivery
    data["Transport Mode"] = re.search(r"Transport Mode:\s*(.+)", text)
    data["Incoterms"] = re.search(r"Incoterm:\s*(.+)", text)
    data["Currency"] = re.search(r"Currency:\s*(.+)", text)
    data["Payment Terms"] = re.search(r"Payment:\s*(.+)", text)
    
    # Product line item
    def extract_value(header, text):
        pattern = rf"{header}\s+([^\t\n]+)"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None
    # Extracting each field like your Subtotal example
    match = re.search(r"ETA Destination\s*\n(.*)", text, re.S)
    if match:
        row = match.group(1).strip().split("\t") if "\t" in match.group(1) else match.group(1).strip().split()
        headers = ["Sales Org","Del Plant","DG Status","Product Description","Form","Pk Size (KG)",
                   "Product Code","Net Weight (Kg)","Sales Currency","Price / Unit","Sales Incoterm","Order Value",
                   "Cust. Reference","ETA Destination"]
        # Map values one by one
        for i, h in enumerate(headers):
            if i < len(row):
                data[h] = row[i]
    headers_none = ["Sales Org","Del Plant","DG Status","Form","Pk Size (KG)",
                   "Sales Currency","Sales Incoterm",
                   "Cust. Reference","ETA Destination"]
    
    for h in headers_none:
        data.pop(h, None)
    
    # Totals
    data["Total Value"] = re.search(r"Total Value\s+([\d.,]+)", text)
    # Banking & Payment Info
    data["Bank Name"] =  re.search(r"Name:\s*(.+)\s+Packing List", text)
    clean_address = None  
    # Extract raw block between Address and City
    match = re.search(r"Address:\s*(.*?)\s*City:", text, re.S)
    if match:
        raw_address = match.group(1).strip()
        # Rule 1: Remove any "words in ALL CAPS" 
        clean_address = re.sub(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b", "", raw_address)
        # Rule 2: Remove extra spaces/commas
        clean_address = re.sub(r"\s{2,}", " ", clean_address).strip()
        clean_address = re.sub(r"\s+,", ",", clean_address)
    data["Bank Address"] = clean_address
    
    data["Bank City"] =  re.search(r"City:\s*(.+)\s", text)
    
    match = re.search(r"Contact:\s*(.+)\s", text)
    data["Contact"] = match.group(1).replace("Attn:", "").strip() if match else None
    data["Email"] =  re.search(r"Email:\s*(.+)\s", text)
    data["Cell Phone"] =  re.search(r"Cell Phone\s*(.+)\s", text)

    return data