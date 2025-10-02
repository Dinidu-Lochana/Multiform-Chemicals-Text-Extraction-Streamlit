import re

def extract_order_confirmation(text):
    """Extract data from Order Confirmation (Format C)"""
    data = {}

    # This pattern captures everything before " PO " as Order Number
    match = re.search(r"Order\s+(?:number|No)[:\s]+(.+?)\s+-?\s*PO\s+(\d+)", text, re.IGNORECASE)
    if match:
        data["Order Number"] = match.group(1).strip().rstrip('-').strip()
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

    def clean_description(text):
        """Remove unwanted characters from product description"""
        if not text:
            return None
        # Remove specific problematic characters
        cleaned = text.replace('Â', '').replace('°', '').replace('™', '').replace('®', '')
        # Remove any remaining non-ASCII characters except common ones
        cleaned = re.sub(r'[^\x00-\x7F]+', '', cleaned)
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    # Try Method 1: Sales number present
    sales_match = re.search(r"Sales number[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    if sales_match:
        data["Product Code"] = sales_match.group(1).strip()
        desc_match = re.search(r"Sales number[:\s].*?\n(.*?)(?=\nIncoterms:)", text, re.IGNORECASE | re.DOTALL)
        data["Product Description"] = clean_description(desc_match.group(1)) if desc_match else None
    else:
        # Method 2: No Sales number
        alt_match = re.search(r"KG\s+[\d.]+\s+[\d,.]+\s*\n(.+?)\s+([A-Z0-9]+)\s*\nIncoterms:", text, re.IGNORECASE)
        if alt_match:
            data["Product Description"] = clean_description(alt_match.group(1))
            data["Product Code"] = alt_match.group(2).strip()
        else:
            data["Product Code"] = None
            data["Product Description"] = None

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