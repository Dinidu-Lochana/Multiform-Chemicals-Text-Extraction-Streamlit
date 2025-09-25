import streamlit as st
import requests
import re
import os
from dotenv import load_dotenv
from openpyxl import load_workbook
import pandas as pd
import time


# Load environment variables
load_dotenv()

def extract_items(text, format_type):
    data = {}

    if format_type == "A":  # Purchase Order Terms & Conditions   PO
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
        match = re.search(r"\b\d+\s+\d+\s+(.+?)\s+(GIV(?:AUDAN)?)\s+(\S+)", text, re.IGNORECASE)

        if match:
            data["Product Description"] = match.group(1).strip()
            data["Product Code"] = match.group(3).strip()

        data["PO against Contract"] = re.search(r"PO against Contract[:\s]+(.+?)(?:\n|$)", text)
        match = re.search(r"As per\s+[Ss]pecification number[:\s]+(\d+)", text)
        data["Specification Number"] = match.group(1).strip() if match else None

        headers_none = ["Unit","Item","PO against Contract"]
        
        for h in headers_none:
            data.pop(h, None)
        

    elif format_type == "B":  # Packing List  Shipping Docs
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

    
    elif format_type == "C":  # Order Confirmation
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
                
        
    elif format_type == "D":  # PROFORMA INVOICE (Excel)
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

    elif format_type == "E":  # COA
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


    elif format_type == "F":  # Packing List

        match = re.search(r"Customer Ref\.\s*:\s*(\S+)\s*-?\s*PO\s+(\d+)", text, re.IGNORECASE)
        if match:
            data["Order Number"] = match.group(1)
            data["Purchase Order Number"] = match.group(2)
        else:
            data["Order Number"] = None
            data["Purchase Order Number"] = None


        # Consignee block
        data["Sold To Code"] = re.search(r"Consignee:\s*Code:\s*(\d+)", text)
        data["Sold To"] = re.search(r"Consignee:.*?Company\s*(.+?)\s*Customer Ref\.", text, re.DOTALL) 
        data["Incoterms"] = re.search(r"Incoterms[:\s]+(.+?)(?:\n|$)", text)
        data["Mode of Transport"] = re.search(r"Mode of Transport[:\s]+(.+?)(?:\n|$)", text)

        match = re.search(r"Total:\s*\d+\s*Packages\s+([\d,]+\.\d{3})", text)

        if match:
            quantity = match.group(1).replace(",", "")
            # Remove trailing zeros after decimal point
            if '.' in quantity:
                quantity = quantity.rstrip('0').rstrip('.')
            data["Net Weight (Kg)"] = quantity
        else:
            data["Net Weight (Kg)"] = None


    # Convert regex results to strings
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

# Load Tika URL from .env
TIKA_URL = TIKA_URL = os.getenv("TIKA_URL")


# -------------------
# Helper to call Tika
# -------------------
def extract_text_from_file(file):
    response = requests.put(
        TIKA_URL,
        headers={"Accept": "text/plain"},
        data=file.read()
    )
    return response.text

# -------------------
# Streamlit UI
# -------------------
st.set_page_config(page_title="Multiform Chemicals (Pvt) Ltd", layout="wide")


st.image("header.png", width=800) 
st.markdown(
    """
    <style>
        .css-18e3th9 {  /* main block container class */
            padding-top: -1000rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Sidebar for file uploads ---

st.sidebar.header("📁 File Upload")
st.sidebar.write("Upload your documents by type, then click **Process All**.")

# File uploaders in sidebar
proforma_invoice_file = st.sidebar.file_uploader("💰 **Proforma Invoice**", type=["pdf", "xlsx"], key="proforma")
order_confirmation_file = st.sidebar.file_uploader("📝 **Order Confirmation**", type=["pdf"], key="oc")
purchase_order_file = st.sidebar.file_uploader("📑 **Purchase Order**", type=["pdf"], key="po")
invoice_file = st.sidebar.file_uploader("📦 **Invoice - Shipping Document**", type=["pdf"], key="invoice")
coa_file = st.sidebar.file_uploader("📑 **Certificate of Analysis**", type=["pdf"], key="coa")
packing_list_file = st.sidebar.file_uploader("📦 **Packing List**", type=["pdf"], key="packing_list")

# Process button in sidebar
process_button = st.sidebar.button("🚀 **Process All**", use_container_width=True)

# Add custom CSS for green process button
st.markdown("""
<style>
.stButton > button {
    background: linear-gradient(90deg, #076e5d, #075649) !important;
    color: white !important;
    border: none !important;
    padding: 12px 20px !important;
    font-weight: bold !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3) !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(90deg, #075649, #076e5d) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4) !important;
}
.stButton > button:focus {
    box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.25) !important;
}
</style>
""", unsafe_allow_html=True)


# Define categories
def get_field_categories():
    return {
        "🛒 Order Details": [
            "Order Number", "Order Type", "Purchase Order Number", "Price / Unit", 
            "Order Value", "Customer Reference", "Product Description", "Product Code", 
            "Material Number", "Specification Number", "Net Weight (Kg)","Sold To", "Sold To Code", "Total Value"
        ],
        "🚢 Commercial & Shipping Details": [
            "Currency", "Payment Terms", "Incoterms", "Transport Mode"
        ],
        "🏦 Bank Details": [
            "Bank Name", "Bank Address", "Bank City", "Contact", "Cell Phone", "Email"
        ],
        
    }

def render_categorized_table(results):
    categories = get_field_categories()
    
    # Collect all possible fields across all docs
    all_fields = set()
    for data in results.values():
        all_fields.update(data.keys())
    
    # --- Custom CSS for Modern Attractive Look with Expandable Sections ---
    st.markdown("""
        <style>
        .table-container {
            width: 100%;
            overflow-x: auto;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
            margin: 5px 0;
        }
        .main-header {
            background: linear-gradient(135deg, #076e5d 0%, #075649 100%);
            color: white;
            padding: 6px;
            border-radius: 8px;
            margin: 5px 0;
            font-weight: bold;
            font-size: 18px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .main-header-table {
            width: 1400px; /* Reduced from 2000px */
            min-width: 1400px;
            border-collapse: separate;
            border-spacing: 0;
            table-layout: fixed;
        }
        .main-header-table th {
            padding: 4px 2px;
            border: none;
            text-align: center;
            vertical-align: middle;
            word-wrap: break-word;
            color: white;
            font-weight: bold;
            font-size: 16px; /* Reduced from 20px */
            line-height: 1.2;
        }
        .main-header-table th:first-child {
            width: 140px; /* Reduced from 200px */
            text-align: center;
        }
        .main-header-table th:not(:first-child) {
            width: 210px; /* Reduced from 300px */
        }
        .category-header {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 8px 12px; /* Reduced padding */
            border-radius: 8px;
            margin: 8px 0 5px 0;
            font-weight: bold;
            font-size: 16px; /* Reduced from 18px */
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .category-header:hover {
            transform: translateY(-1px);
            box-shadow: 0 3px 12px rgba(0,0,0,0.12);
        }
        .green-cell {
            background-color: #d4edda;
            color: #155724;
            padding: 4px 8px; /* Reduced padding */
            border-radius: 12px;
            display: inline-block;
            margin: 1px;
            min-width: 50px; /* Reduced from 70px */
            text-align: center;
            border: 1px solid #c3e6cb;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            font-weight: 500;
            word-wrap: break-word;
            max-width: 140px; /* Reduced from 180px */
            font-size: 14px; /* Added smaller font size */
            line-height: 1.2;
        }
        .red-cell {
            background-color: #f8d7da;
            color: #721c24;
            padding: 4px 8px; /* Reduced padding */
            border-radius: 12px;
            display: inline-block;
            margin: 1px;
            min-width: 50px; /* Reduced from 70px */
            text-align: center;
            border: 1px solid #f5c6cb;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            font-weight: 500;
            word-wrap: break-word;
            max-width: 140px; /* Reduced from 180px */
            font-size: 14px; /* Added smaller font size */
            line-height: 1.2;
        }
        .field-column {
            font-weight: bold;
            padding: 6px 8px; /* Reduced padding */
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 6px;
            text-align: left;
            border-left: 3px solid #007bff;
            width: 140px; /* Reduced from 200px */
            font-size: 11px; /* Added smaller font size */
            line-height: 1.3;
        }
        .comparison-table {
            width: 1400px; /* Reduced from 2000px */
            min-width: 1400px;
            border-collapse: separate;
            border-spacing: 0 4px; /* Reduced from 8px */
            margin: 8px 0; /* Reduced margin */
            table-layout: fixed;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }
        .comparison-table th, .comparison-table td {
            padding: 6px 4px; /* Reduced from 12px 8px */
            border: none;
            text-align: center;
            vertical-align: middle;
            word-wrap: break-word;
            overflow: hidden;
            font-size: 14px; /* Added smaller font size */
            line-height: 1.2;
        }
        .comparison-table th:first-child, .comparison-table td:first-child {
            width: 140px; /* Reduced from 200px */
            text-align: center;
        }
        .comparison-table th:not(:first-child), .comparison-table td:not(:first-child) {
            width: 210px; /* Reduced from 300px */
        }
        .comparison-table th {
            background: linear-gradient(90deg, #f8f9fa, #e9ecef);
            color: #495057;
            font-weight: bold;
            border-bottom: 1px solid #dee2e6; /* Reduced from 2px */
            font-size: 15px; /* Even smaller for headers */
        }
        .comparison-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        .comparison-table tr:hover {
            background-color: #e3f2fd;
            transform: scale(1.002); /* Reduced from 1.005 */
            transition: all 0.2s ease-in-out;
            box-shadow: 0 1px 5px rgba(0,0,0,0.08);
        }
        .no-data-message {
            text-align: center;
            padding: 20px; /* Reduced from 30px */
            color: #6c757d;
            font-style: italic;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 6px;
            margin: 8px 0; /* Reduced margin */
            font-size: 12px; /* Added smaller font size */
        }

        /* Scrollbar styling */
        .table-container::-webkit-scrollbar {
            height: 8px; /* Reduced from 12px */
        }
        .table-container::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        .table-container::-webkit-scrollbar-thumb {
            background: linear-gradient(90deg, #076e5d, #075649);
            border-radius: 4px;
        }
        .table-container::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(90deg, #075649, #076e5d);
        }

        /* Additional compact styling */
        .stExpander > div > div > div {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Display main header first with scroll container
    main_header_html = '''
    <div class="table-container">
        <div class="main-header">
            <table class="main-header-table">
                <tr>
                    <th>Data Field</th>
                    <th>💰 Proforma Invoice<br>(PI)</th>
                    <th>📝 Order Confirmation<br>(OC)</th>
                    <th>📑 Purchase Order<br>(PO)</th>
                    <th>📦 Invoice</th>
                    <th>📑 Certificate of Analysis<br>(COA)</th>
                    <th>📦 Packing List<br>(PL)</th>
                </tr>
            </table>
        </div>
    </div>
    '''
    st.markdown(main_header_html, unsafe_allow_html=True)
    
    # Process each category
    for category_name, category_fields in categories.items():
        # Check if this category has any data
        category_has_data = False
        category_data = []
        
        for field in category_fields:
            if field in all_fields:
                category_has_data = True
                
                proforma_value = results.get("Proforma Invoice", {}).get(field, "")
                order_conf_value = results.get("Order Confirmation", {}).get(field, "")
                purchase_order_value = results.get("Purchase Order", {}).get(field, "")
                invoice_value = results.get("Invoice - Shipping Document", {}).get(field, "")
                coa_value = results.get("Certificate of Analysis", {}).get(field, "")
                packing_list_value = results.get("Packing List", {}).get(field, "")
                
                category_data.append({
                    'field': field,
                    'proforma': proforma_value,
                    'order_conf': order_conf_value,
                    'purchase_order': purchase_order_value,
                    'invoice': invoice_value,
                    'coa': coa_value,
                    'packing_list': packing_list_value
                })
        
        # Only show category if it has data - START COLLAPSED (expanded=False)
        if category_has_data:
            with st.expander(category_name, expanded=False):
                if category_data:
                    # Build HTML table for this category with scroll container
                    html_content = '<div class="table-container"><table class="comparison-table">'
                    
                    for row_data in category_data:
                        field = row_data['field']
                        proforma_value = row_data['proforma']
                        order_conf_value = row_data['order_conf']
                        purchase_order_value = row_data['purchase_order']
                        invoice_value = row_data['invoice']
                        coa_value = row_data['coa']
                        packing_list_value = row_data['packing_list']
                        
                        html_content += f'<tr><td class="field-column">{field}</td>'
                        
                        # Helper function to determine cell styling
                        def get_cell_display(value, reference_value, secondary_reference=None):
                            if value:
                                if reference_value and value == reference_value:
                                    return f'<span class="green-cell">{value}</span>'
                                elif not reference_value and secondary_reference and value == secondary_reference:
                                    return f'<span class="green-cell">{value}</span>'
                                elif reference_value and value != reference_value:
                                    return f'<span class="red-cell">{value}</span>'
                                elif not reference_value and secondary_reference and value != secondary_reference:
                                    return f'<span class="red-cell">{value}</span>'
                                else:
                                    return f'<span class="green-cell">{value}</span>'
                            else:
                                return '-'
                        
                        # Proforma Invoice column (base reference)
                        proforma_display = f'<span class="green-cell">{proforma_value}</span>' if proforma_value else '-'
                        html_content += f'<td>{proforma_display}</td>'
                        
                        # Other columns compared against proforma (or purchase order if proforma is empty)
                        order_conf_display = get_cell_display(order_conf_value, proforma_value, purchase_order_value)
                        html_content += f'<td>{order_conf_display}</td>'
                        
                        purchase_order_display = get_cell_display(purchase_order_value, proforma_value)
                        html_content += f'<td>{purchase_order_display}</td>'
                        
                        invoice_display = get_cell_display(invoice_value, proforma_value, purchase_order_value)
                        html_content += f'<td>{invoice_display}</td>'
                        
                        coa_display = get_cell_display(coa_value, proforma_value, purchase_order_value)
                        html_content += f'<td>{coa_display}</td>'
                        
                        packing_list_display = get_cell_display(packing_list_value, proforma_value, purchase_order_value)
                        html_content += f'<td>{packing_list_display}</td>'
                        
                        html_content += '</tr>'
                    
                    html_content += '</table></div>'
                    st.markdown(html_content, unsafe_allow_html=True)
                else:
                    st.markdown('<div class="no-data-message">No data available for this category</div>', unsafe_allow_html=True)

st.markdown("""
<style>
/* Existing CSS styles... */

/* Processing Animation Styles */
.processing-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 15px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    margin: 20px 0;
}

.processing-title {
    font-size: 24px;
    font-weight: bold;
    color: #076e5d;
    margin-bottom: 10px;
    text-align: center;
}

.processing-subtitle {
    font-size: 16px;
    color: #666;
    margin-bottom: 30px;
    text-align: center;
}

.spinner {
    width: 60px;
    height: 60px;
    border: 4px solid #e3e3e3;
    border-top: 4px solid #076e5d;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 20px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.progress-container {
    width: 100%;
    max-width: 400px;
    margin-bottom: 20px;
}

.progress-bar {
    width: 100%;
    height: 20px;
    background-color: #e0e0e0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #076e5d, #075649);
    border-radius: 10px;
    transition: width 0.5s ease-in-out;
    box-shadow: 0 2px 8px rgba(7, 110, 93, 0.3);
}

.progress-text {
    text-align: center;
    margin-top: 10px;
    font-size: 18px;
    font-weight: bold;
    color: #076e5d;
}

.current-file {
    text-align: center;
    font-size: 14px;
    color: #666;
    margin-top: 5px;
    font-style: italic;
}

.dots {
    display: inline-block;
}

.dots::after {
    content: '';
    animation: dots 1.5s infinite;
}

@keyframes dots {
    0%, 20% { content: ''; }
    40% { content: '.'; }
    60% { content: '..'; }
    80%, 100% { content: '...'; }
}
</style>
""", unsafe_allow_html=True)

# --- Process button logic ---
if process_button:
    # Count total files to process
    files_to_process = []
    if proforma_invoice_file:
        files_to_process.append(("Proforma Invoice", proforma_invoice_file, "D"))
    if order_confirmation_file:
        files_to_process.append(("Order Confirmation", order_confirmation_file, "C"))
    if purchase_order_file:
        files_to_process.append(("Purchase Order", purchase_order_file, "A"))
    if invoice_file:
        files_to_process.append(("Invoice - Shipping Document", invoice_file, "B"))
    if coa_file:
        files_to_process.append(("Certificate of Analysis", coa_file, "E"))
    if packing_list_file:
        files_to_process.append(("Packing List", packing_list_file, "F"))
    
    if not files_to_process:
        st.error("No documents were uploaded!")
    else:
        total_files = len(files_to_process)
        
        # Create containers for the processing animation
        processing_container = st.empty()
        
        # Show initial processing state
        processing_html = f"""
        <div class="processing-container">
            <div class="processing-title">Processing Documents</div>
            <div class="processing-subtitle">Extracting data from your uploaded files<span class="dots"></span></div>
            <div class="spinner"></div>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text">0%</div>
                <div class="current-file">Initializing...</div>
            </div>
        </div>
        """
        processing_container.markdown(processing_html, unsafe_allow_html=True)
        
        # Process files one by one
        results = {}
        
        for i, (doc_type, file, format_type) in enumerate(files_to_process):
            # Update progress
            progress_percentage = int((i / total_files) * 100)
            
            # Update processing display
            processing_html = f"""
            <div class="processing-container">
                <div class="processing-title">Processing Documents</div>
                <div class="processing-subtitle">Extracting data from your uploaded files<span class="dots"></span></div>
                <div class="spinner"></div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {progress_percentage}%"></div>
                    </div>
                    <div class="progress-text">{progress_percentage}%</div>
                    <div class="current-file">Processing: {doc_type}...</div>
                </div>
            </div>
            """
            processing_container.markdown(processing_html, unsafe_allow_html=True)
            
            # Add a small delay to make the animation visible
            import time
            time.sleep(0.5)
            
            # Extract text and process
            text = extract_text_from_file(file)
            results[doc_type] = extract_items(text, format_type)
        
        # Show completion
        processing_html = f"""
        <div class="processing-container">
            <div class="processing-title">✅ Processing Complete!</div>
            <div class="processing-subtitle">Successfully extracted data from {total_files} document(s)</div>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 100%"></div>
                </div>
                <div class="progress-text">100%</div>
                <div class="current-file">All documents processed successfully!</div>
            </div>
        </div>
        """
        processing_container.markdown(processing_html, unsafe_allow_html=True)
        
        # Small delay before showing results
        time.sleep(1)
        
        # Clear the processing container and show results
        processing_container.empty()
        
        # Render the results table
        render_categorized_table(results)
