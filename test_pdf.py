import os
from datetime import date
from pdf_generator import generate_bill_pdf

os.makedirs("test_output", exist_ok=True)

test_bill = {
    'bill_number': 'SS-2457',
    'bill_date': date(2026, 8, 31),
    'km': 45200,
    'subtotal': 6450.0,
    'discount': 0.0,
    'tax': 0.0,
    'total': 6450.0,
    'garage_phones': '9422711826, 9834196573'
}

test_customer = {
    'name': 'Dudhsan Madam',
    'mobile': '9876543210',
    'address': 'Nanded'
}

test_vehicle = {
    'vehicle_number': 'MH-26-S-0031',
    'model': 'Maruti Swift'
}

test_items = [
    {'description': 'Horn, Head lamp bulb change, with parts.', 'amount': 2300.0},
    {'description': 'Gear box removing refitting.', 'amount': 2000.0},
    {'description': 'Main oil seal change.', 'amount': 0.0},
    {'description': 'Kothari Auto parts Bill. oil + Anabond.', 'amount': 1500.0},
    {'description': 'Mobis Bill. (oil seal).', 'amount': 650.0}
]

output_pdf = os.path.join("test_output", "test_bill.pdf")
generate_bill_pdf(test_bill, test_customer, test_vehicle, test_items, output_pdf)
print(f"SUCCESS: Generated test PDF at {output_pdf}, size: {os.path.getsize(output_pdf)} bytes")
