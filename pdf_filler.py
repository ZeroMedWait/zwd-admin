from pdfrw import PdfReader, PdfWriter, PdfName, PdfObject

# Load the PDF template
template = PdfReader("Sample-Fillable-PDF.pdf")

# Map PDF field names to values
data = {
    "Name": "John Doe",
    "Age\\t of Dependent": "24 years",
    "Name of Dependent": "Jane Doe",
    "Option 1": PdfName('On'),   # Checkbox checked
    "Option 2": PdfName('Off'),  # Checkbox unchecked
    "Option 3": PdfName('On'),   # Checkbox checked
    "Dropdown2": "Item2",        # Dropdown value (if needed)
}

# Fill the fields
for page in template.pages:
    annotations = page.get("/Annots")
    if annotations:
        for annotation in annotations:
            if annotation.get("/Subtype") == "/Widget" and annotation.get("/T"):
                field_name = annotation.get("/T")[1:-1]
                if field_name in data:
                    value = data[field_name]
                    print(f"Filling: {field_name} = {value}")
                    
                    # For buttons (checkboxes/radio), also set appearance state
                    if annotation.get('/FT') == '/Btn':
                        annotation.update({
                            PdfName('V'): value,
                            PdfName('AS'): value,  # Appearance state
                            PdfName('Ff'): 1,  # Read-only flag

                        })
                    else:
                        # For text fields
                        annotation.update({
                            PdfName('V'): value,
                            PdfName('AP'): None,
                            PdfName('Ff'): 1,  # Read-only flag
                        })

# Tell PDF reader to regenerate appearances
if template.Root.AcroForm:
    template.Root.AcroForm.update({PdfName('NeedAppearances'): PdfObject('true')})

# Save the filled PDF
PdfWriter().write("filled.pdf", template)

print("\nPDF filled successfully!")
