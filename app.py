import streamlit as st
import requests
import re
import os
from dotenv import load_dotenv
from openpyxl import load_workbook
import pandas as pd
import time

# Import the extractors
from extractors import (
    extract_purchase_order,
    extract_packing_list,
    extract_order_confirmation,
    extract_proforma_invoice,
    extract_coa,
    extract_packing_list_f
)
from utils import convert_regex_results_to_strings

# Load environment variables
load_dotenv()

def extract_items(text, format_type):
    """
    Main extraction function that routes to appropriate extractor
    """
    data = {}
    
    if format_type == "A":  # Purchase Order Terms & Conditions   PO
        data = extract_purchase_order(text)
        
    elif format_type == "B":  # Packing List  Shipping Docs
        data = extract_packing_list(text)
    
    elif format_type == "C":  # Order Confirmation
        data = extract_order_confirmation(text)
        
    elif format_type == "D":  # PROFORMA INVOICE (Excel)
        data = extract_proforma_invoice(text)

    elif format_type == "E":  # COA
        data = extract_coa(text)

    elif format_type == "F":  # Packing List
        data = extract_packing_list_f(text)

    # Convert regex results to strings
    data = convert_regex_results_to_strings(data)
    
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
        .data-cell {
           display: inline-flex;           /* Was: flex */
            align-items: center;            
            justify-content: center;        
            gap: 4px;                       /* Space between text and icon */
            padding: 4px 8px;
            border-radius: 12px;
            min-width: 50px;
            max-width: 140px;
            font-size: 14px;
            background-color: #ffffff;
            color: #495057;
            border: 1px solid #dee2e6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            word-break: break-word;
        }
        .data-cell .text-content {
            flex: 1;
            margin-right: 5px;
        }
        .status-icon {
            display: inline-block;          /* Added this line */
            vertical-align: middle;         /* Ensures vertical alignment */
            margin-left: 4px;
            width: 16px;
            height: 16px;
            min-width: 16px;
            min-height: 16px;
            max-width: 16px;
            max-height: 16px;
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
            width: 1350px; /* Reduced from 2000px */
            min-width: 1350px;
            border-collapse: separate;
            border-spacing: 0 4px; /* Reduced from 8px */
            margin: 8px 0; /* Reduced margin */
            table-layout: fixed;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06); # Shadow
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
            width: 130px; /* Reduced from 200px */
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
                        
                        # Helper function to determine cell styling with icons
                        def get_cell_display(value, reference_value, secondary_reference=None):
                            # Simple and reliable SVG icons
                            tick_icon = '''<svg class="status-icon" width="16" height="16" viewBox="0 0 16 16" style="display: inline-block; vertical-align: middle;">
                                <circle cx="8" cy="8" r="8" fill="#28a745"/>
                                <polyline points="4.5,8 7,10.5 11.5,6" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>'''
                            
                            cross_icon = '''<svg class="status-icon" width="16" height="16" viewBox="0 0 16 16" style="display: inline-block; vertical-align: middle;">
                                <circle cx="8" cy="8" r="8" fill="#dc3545"/>
                                <line x1="5" y1="5" x2="11" y2="11" stroke="white" stroke-width="2" stroke-linecap="round"/>
                                <line x1="11" y1="5" x2="5" y2="11" stroke="white" stroke-width="2" stroke-linecap="round"/>
                            </svg>'''
                            
                            if value:
                                if reference_value and value == reference_value:
                                    return f'<div class="data-cell"><span class="text-content">{value}</span>{tick_icon}</div>'
                                elif not reference_value and secondary_reference and value == secondary_reference:
                                    return f'<div class="data-cell"><span class="text-content">{value}</span>{tick_icon}</div>'
                                elif reference_value and value != reference_value:
                                    return f'<div class="data-cell"><span class="text-content">{value}</span>{cross_icon}</div>'
                                elif not reference_value and secondary_reference and value != secondary_reference:
                                    return f'<div class="data-cell"><span class="text-content">{value}</span>{cross_icon}</div>'
                                else:
                                    return f'<div class="data-cell"><span class="text-content">{value}</span>{tick_icon}</div>'
                            else:
                                return '-'
                        
                        # Proforma Invoice column (base reference) - add tick icon
                        tick_icon = '''<svg class="status-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" fill="#28a745"/>
                            <path d="M8 12l3 3 5-6" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                        </svg>'''
                        proforma_display = f'<div class="data-cell"><span class="text-content">{proforma_value}</span>{tick_icon}</div>' if proforma_value else '-'
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