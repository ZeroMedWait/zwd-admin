from pdfrw import PdfReader
import json

# Load the PDF template
template = PdfReader("CR1-Blank-With-Fields.pdf")

# Collect all field names
fields = {}

# Check AcroForm for fields (most reliable method for multi-page PDFs)
if template.Root.AcroForm and template.Root.AcroForm.Fields:
    for field in template.Root.AcroForm.Fields:
        if field.T:
            field_name = field.T[1:-1]  # Remove parentheses
            fields[field_name] = ""

# Print as JSON
print(json.dumps(fields, indent=4, ensure_ascii=False))