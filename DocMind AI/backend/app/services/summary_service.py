import os
from typing import Dict, Any

try:
    from transformers import pipeline
except ImportError:
    pipeline = None

from backend.app.config import settings

class SummaryService:
    def __init__(self):
        self.summarizer = None
        self.fallback = settings.AI_FALLBACK_MODE

        if not self.fallback:
            try:
                if pipeline:
                    self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            except Exception as e:
                print(f"Warning: Failed to load BART summarization pipeline: {e}")
                self.fallback = True

    def generate_summary(self, doc_type: str, extracted_data: Dict[str, Any], lang: str = "en") -> str:
        """
        Generates a readable summary of the document.
        Supports both English ("en") and Hindi ("hi") outputs.
        """
        if not extracted_data:
            return "No data extracted to summarize." if lang == "en" else "संक्षेप करने के लिए कोई डेटा नहीं मिला।"

        # Fallback to high-quality template synthesis
        if lang == "hi":
            return self._generate_hindi_summary(doc_type, extracted_data)
        return self._generate_english_summary(doc_type, extracted_data)

    def _generate_english_summary(self, doc_type: str, data: Dict[str, Any]) -> str:
        summary_parts = []
        
        if doc_type == "Aadhaar Card":
            name = data.get("name", "N/A")
            num = data.get("aadhaar_number", "N/A")
            dob = data.get("dob", "N/A")
            gen = data.get("gender", "N/A")
            summary_parts.append(f"This is an Aadhaar Card issued to {name} ({gen}) with Date of Birth {dob}.")
            summary_parts.append(f"The unique Aadhaar number is {num}.")
            
        elif doc_type == "PAN Card":
            name = data.get("name", "N/A")
            fname = data.get("father_name", "N/A")
            dob = data.get("dob", "N/A")
            pan = data.get("pan_number", "N/A")
            summary_parts.append(f"This is a Permanent Account Number (PAN) Card belonging to {name}, son of {fname}.")
            summary_parts.append(f"The cardholder was born on {dob} and holds PAN Number {pan}.")
            
        elif doc_type == "Passport":
            name = f"{data.get('given_names', '')} {data.get('surname', '')}".strip() or "N/A"
            num = data.get("passport_number", "N/A")
            dob = data.get("dob", "N/A")
            summary_parts.append(f"This is a Passport document for {name}. Passport number is {num} and Date of Birth is {dob}.")
            
        elif doc_type == "Driving License":
            name = data.get("name", "N/A")
            dl_num = data.get("dl_number", "N/A")
            valid = data.get("validity", "N/A")
            summary_parts.append(f"Driving License belonging to {name} under license number {dl_num}.")
            summary_parts.append(f"The license is valid until {valid}.")
            
        elif doc_type == "Invoice":
            inv_num = data.get("invoice_number", "N/A")
            bill_to = data.get("bill_to", "N/A")
            amount = data.get("total_amount", "N/A")
            date = data.get("invoice_date", "N/A")
            summary_parts.append(f"Invoice {inv_num} issued on {date} billed to {bill_to}.")
            summary_parts.append(f"The total due amount is {amount}.")
            
        elif doc_type == "Salary Slip":
            name = data.get("employee_name", "N/A")
            emp_id = data.get("employee_id", "N/A")
            net = data.get("net_salary", "N/A")
            month = data.get("month", "N/A")
            summary_parts.append(f"Payslip for {name} (Employee ID: {emp_id}) for the month of {month}.")
            summary_parts.append(f"The Net Salary disbursed is {net}.")
            
        elif doc_type == "Bank Statement":
            name = data.get("holder_name", "N/A")
            acc = data.get("account_number", "N/A")
            bal = data.get("closing_balance", "N/A")
            period = data.get("period", "N/A")
            summary_parts.append(f"Bank Account Statement for {name} (Account No: {acc}) spanning {period}.")
            summary_parts.append(f"The closing ledger balance is {bal}.")
            
        elif doc_type == "Utility Bill":
            acc = data.get("account_number", "N/A")
            amt = data.get("payable_amount", "N/A")
            due = data.get("due_date", "N/A")
            summary_parts.append(f"Utility invoice for Account Number {acc}. The total payable amount is {amt} with a due date of {due}.")
            
        elif doc_type == "Cheque":
            payee = data.get("payee", "N/A")
            amt = data.get("amount", "N/A")
            num = data.get("cheque_number", "N/A")
            acc = data.get("account_no", "N/A")
            summary_parts.append(f"Bank Cheque {num} drawn on Account {acc} payable to {payee} for a sum of {amt}.")
            
        else:
            summary_parts.append(f"This is a general {doc_type} containing keys: {', '.join(data.keys())}.")

        return " ".join(summary_parts)

    def _generate_hindi_summary(self, doc_type: str, data: Dict[str, Any]) -> str:
        summary_parts = []
        
        if doc_type == "Aadhaar Card":
            name = data.get("name", "एन/ए")
            num = data.get("aadhaar_number", "एन/ए")
            dob = data.get("dob", "एन/ए")
            gen = "पुरुष" if data.get("gender") == "Male" else "महिला"
            summary_parts.append(f"यह एक आधार कार्ड है जो {name} ({gen}) को जारी किया गया है। जन्म तिथि {dob} है।")
            summary_parts.append(f"विशिष्ट आधार संख्या {num} है।")
            
        elif doc_type == "PAN Card":
            name = data.get("name", "एन/ए")
            fname = data.get("father_name", "एन/ए")
            dob = data.get("dob", "एन/ए")
            pan = data.get("pan_number", "एन/ए")
            summary_parts.append(f"यह स्थायी खाता संख्या (PAN) कार्ड है जो {name} (पिता: {fname}) का है।")
            summary_parts.append(f"धारक की जन्म तिथि {dob} है और पैन संख्या {pan} है।")
            
        elif doc_type == "Passport":
            name = f"{data.get('given_names', '')} {data.get('surname', '')}".strip() or "एन/ए"
            num = data.get("passport_number", "एन/ए")
            dob = data.get("dob", "एन/ए")
            summary_parts.append(f"यह {name} का पासपोर्ट है। पासपोर्ट संख्या {num} है और जन्म तिथि {dob} है।")
            
        elif doc_type == "Driving License":
            name = data.get("name", "एन/ए")
            dl_num = data.get("dl_number", "एन/ए")
            valid = data.get("validity", "एन/ए")
            summary_parts.append(f"चालक लाइसेंस संख्या {dl_num} जो {name} के नाम पर है।")
            summary_parts.append(f"यह लाइसेंस {valid} तक वैध है।")
            
        elif doc_type == "Invoice":
            inv_num = data.get("invoice_number", "एन/ए")
            bill_to = data.get("bill_to", "एन/ए")
            amount = data.get("total_amount", "एन/ए")
            date = data.get("invoice_date", "एन/ए")
            summary_parts.append(f"चालान (Invoice) संख्या {inv_num} जो {date} को {bill_to} के नाम जारी किया गया था।")
            summary_parts.append(f"कुल देय राशि {amount} है।")
            
        elif doc_type == "Salary Slip":
            name = data.get("employee_name", "एन/ए")
            emp_id = data.get("employee_id", "एन/ए")
            net = data.get("net_salary", "एन/ए")
            month = data.get("month", "एन/ए")
            summary_parts.append(f"कर्मचारी {name} (आईडी: {emp_id}) की माह {month} की वेतन पर्ची।")
            summary_parts.append(f"कुल शुद्ध वेतन (Net Salary) {net} है।")
            
        elif doc_type == "Bank Statement":
            name = data.get("holder_name", "एन/ए")
            acc = data.get("account_number", "एन/ए")
            bal = data.get("closing_balance", "एन/ए")
            period = data.get("period", "एन/ए")
            summary_parts.append(f"{name} (खाता संख्या: {acc}) का बैंक खाता विवरण {period} तक।")
            summary_parts.append(f"अंतिम शेष राशि (Closing Balance) {bal} है।")
            
        elif doc_type == "Utility Bill":
            acc = data.get("account_number", "एन/ए")
            amt = data.get("payable_amount", "एन/ए")
            due = data.get("due_date", "एन/ए")
            summary_parts.append(f"उपयोगिता बिल खाता संख्या {acc} के लिए। कुल देय राशि {amt} है और भुगतान की अंतिम तिथि {due} है।")
            
        elif doc_type == "Cheque":
            payee = data.get("payee", "एन/ए")
            amt = data.get("amount", "एन/ए")
            num = data.get("cheque_number", "एन/ए")
            acc = data.get("account_no", "एन/ए")
            summary_parts.append(f"बैंक चेक संख्या {num} खाता संख्या {acc} से {payee} को {amt} भुगतान हेतु जारी किया गया है।")
            
        else:
            summary_parts.append(f"यह एक सामान्य {doc_type} है जिसमें फ़ील्ड शामिल हैं: {', '.join(data.keys())}।")

        return " ".join(summary_parts)

summary_service = SummaryService()
