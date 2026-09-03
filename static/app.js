// Global State
let itemCounter = 0;
let currentBillId = null;
let currentBillNumber = null;
let currentCustomerMobile = null;
let currentVehicleNumber = null;

// Initialize Page
window.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    initDate();
    fetchNextBillNumber();
    addParticularRow(); // Add first item row
    
    // Attach Event Listeners
    document.getElementById('add-item-btn').addEventListener('click', () => addParticularRow());
    document.getElementById('submit-bill-btn').addEventListener('click', showConfirmation);
    document.getElementById('confirm-cancel').addEventListener('click', hideConfirmation);
    document.getElementById('confirm-ok').addEventListener('click', generateBill);
    document.getElementById('new-bill-btn').addEventListener('click', resetForm);
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    
    // Auto-update calculations
    document.getElementById('discount-input').addEventListener('input', updateTotals);
    document.getElementById('tax-input').addEventListener('input', updateTotals);
});

// Authentication Guard
async function checkAuth() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if (!data.logged_in || data.role !== 'owner') {
            window.location.href = '/login.html';
        }
    } catch (e) {
        window.location.href = '/login.html';
    }
}

// Initialize date field to today
function initDate() {
    const today = new Date();
    const yyyy = today.getFullYear();
    let mm = today.getMonth() + 1;
    let dd = today.getDate();
    
    if (dd < 10) dd = '0' + dd;
    if (mm < 10) mm = '0' + mm;
    
    document.getElementById('bill-date').value = `${yyyy}-${mm}-${dd}`;
}

// Fetch Next Bill Number
async function fetchNextBillNumber() {
    try {
        const res = await fetch('/api/bills/next-number');
        const data = await res.json();
        if (data.bill_number) {
            document.getElementById('bill-no-badge').innerText = `Bill No: ${data.bill_number}`;
        }
    } catch (e) {
        console.error("Error fetching bill number", e);
    }
}

// Add Dynamic Particular Row
function addParticularRow() {
    itemCounter++;
    const container = document.getElementById('items-container');
    const rowId = `item-row-${itemCounter}`;
    
    const rowHTML = `
        <div id="${rowId}" class="flex items-center space-x-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span class="text-sm font-bold text-slate-400 w-6 text-center item-sr-no"></span>
            
            <div class="flex-1">
                <input 
                    type="text" 
                    placeholder="Work Particulars / Parts fitted" 
                    class="w-full py-2 px-3 border border-slate-300 rounded-lg text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none item-desc"
                    required
                >
            </div>
            
            <div class="w-28">
                <input 
                    type="number" 
                    inputmode="decimal"
                    min="0"
                    step="0.01"
                    placeholder="Amount" 
                    class="w-full py-2 px-3 border border-slate-300 rounded-lg text-sm text-right font-medium focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none item-amount"
                    required
                >
            </div>
            
            <button 
                type="button" 
                onclick="removeParticularRow('${rowId}')"
                class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors remove-btn"
                title="Delete Row"
            >
                <i class="fa-solid fa-trash-can text-base"></i>
            </button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', rowHTML);
    
    // Attach change listener to amount
    document.querySelector(`#${rowId} .item-amount`).addEventListener('input', updateTotals);
    
    reindexRows();
    updateTotals();
}

// Remove Particular Row
function removeParticularRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.remove();
        reindexRows();
        updateTotals();
    }
}

// Reindex the Sr. No labels
function reindexRows() {
    const rows = document.querySelectorAll('#items-container > div');
    rows.forEach((row, index) => {
        row.querySelector('.item-sr-no').innerText = index + 1;
    });
    
    // Disable delete if only one row left
    const removeButtons = document.querySelectorAll('.remove-btn');
    removeButtons.forEach(btn => {
        btn.disabled = rows.length <= 1;
        if (rows.length <= 1) {
            btn.classList.add('opacity-30', 'cursor-not-allowed');
        } else {
            btn.classList.remove('opacity-30', 'cursor-not-allowed');
        }
    });
}

// Compute and Update totals
function updateTotals() {
    let subtotal = 0;
    const amounts = document.querySelectorAll('.item-amount');
    
    amounts.forEach(el => {
        const val = parseFloat(el.value) || 0;
        subtotal += val;
    });
    
    const discount = parseFloat(document.getElementById('discount-input').value) || 0;
    const tax = parseFloat(document.getElementById('tax-input').value) || 0;
    
    let total = subtotal - discount + tax;
    if (total < 0) total = 0;
    
    document.getElementById('subtotal-label').innerText = `₹${subtotal.toFixed(2)}`;
    document.getElementById('total-label').innerText = `₹${total.toFixed(2)}`;
}

// Get form data and validate
function getFormDataAndValidate() {
    const errorBanner = document.getElementById('validation-error');
    errorBanner.classList.add('hidden');
    
    const custName = document.getElementById('cust-name').value.trim();
    const custMobile = document.getElementById('cust-mobile').value.trim();
    const custAddress = document.getElementById('cust-address').value.trim();
    const vehNumber = document.getElementById('veh-number').value.trim().toUpperCase();
    const vehModel = document.getElementById('veh-model').value.trim();
    const vehKm = document.getElementById('veh-km').value.trim();
    const billDate = document.getElementById('bill-date').value;
    const discount = parseFloat(document.getElementById('discount-input').value) || 0;
    const tax = parseFloat(document.getElementById('tax-input').value) || 0;
    
    // Validations
    if (!custName) return setError("Customer Name is required.");
    if (!custMobile) return setError("Mobile number is required.");
    if (custMobile.length !== 10 || !/^\d+$/.test(custMobile)) {
        return setError("Please enter a valid 10-digit Indian Mobile Number.");
    }
    if (!vehNumber) return setError("Vehicle Number is required.");
    if (vehKm === '' || parseInt(vehKm) < 0) return setError("Please enter a valid Odometer (KM) reading.");
    if (!billDate) return setError("Please select a valid Bill Date.");
    if (discount < 0 || tax < 0) return setError("Discount and Tax amounts cannot be negative.");
    
    // Gather Items
    const items = [];
    const itemRows = document.querySelectorAll('#items-container > div');
    let hasItemError = false;
    
    itemRows.forEach(row => {
        const desc = row.querySelector('.item-desc').value.trim();
        const amtVal = row.querySelector('.item-amount').value.trim();
        
        if (!desc) {
            hasItemError = true;
            setError("Particular description cannot be blank.");
            return;
        }
        if (amtVal === '' || parseFloat(amtVal) < 0) {
            hasItemError = true;
            setError("Amount cannot be negative or blank.");
            return;
        }
        
        items.push({
            description: desc,
            amount: parseFloat(amtVal)
        });
    });
    
    if (hasItemError) return null;
    if (items.length === 0) return setError("At least one bill item is required.");
    
    return {
        customer: { name: custName, mobile: custMobile, address: custAddress },
        vehicle: { vehicle_number: vehNumber, make: "", model: vehModel },
        bill_date: billDate,
        km: parseInt(vehKm),
        discount,
        tax,
        items
    };
}

function setError(msg) {
    const errorBanner = document.getElementById('validation-error');
    errorBanner.innerText = msg;
    errorBanner.classList.remove('hidden');
    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return null;
}

// Modal Toggle Helpers
function showConfirmation() {
    const data = getFormDataAndValidate();
    if (data) {
        document.getElementById('confirm-modal').classList.remove('hidden');
    }
}

function hideConfirmation() {
    document.getElementById('confirm-modal').classList.add('hidden');
}

// Submit Bill API
async function generateBill() {
    hideConfirmation();
    const data = getFormDataAndValidate();
    if (!data) return;
    
    // Disable button to prevent double submission
    const submitBtn = document.getElementById('submit-bill-btn');
    submitBtn.disabled = true;
    submitBtn.innerText = "Generating...";
    
    try {
        const response = await fetch('/api/bills', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const resData = await response.json();
        if (response.ok) {
            // Save state for actions
            currentBillId = resData.bill_id;
            currentBillNumber = resData.bill_number;
            currentCustomerMobile = data.customer.mobile;
            currentVehicleNumber = data.vehicle.vehicle_number;
            
            // Switch Screens
            document.getElementById('success-bill-no').innerText = `Bill No: ${currentBillNumber}`;
            document.getElementById('form-container').classList.add('hidden');
            document.getElementById('success-container').classList.remove('hidden');
            
            // Update Buttons
            document.getElementById('view-pdf-btn').onclick = () => {
                window.open(`/api/bills/${currentBillId}/pdf`, '_blank');
            };
            document.getElementById('share-pdf-btn').onclick = sharePDF;
        } else {
            setError(resData.error || "Failed to create bill. Try again.");
        }
    } catch (err) {
        setError("Something went wrong. Please check your connection and try again.");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fa-solid fa-receipt mr-2 text-xl"></i> Generate Bill`;
    }
}

// PDF Sharing Integration (Web Share API with Fallback)
async function sharePDF() {
    try {
        const pdfUrl = `/api/bills/${currentBillId}/pdf`;
        
        // Fetch the PDF blob
        const res = await fetch(pdfUrl);
        const blob = await res.blob();
        
        const fileName = `${currentBillNumber}.pdf`;
        const file = new File([blob], fileName, { type: 'application/pdf' });
        
        // Check if Web Share API is available and can share file
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({
                files: [file],
                title: `Invoice ${currentBillNumber}`,
                text: `Sumangal Services Bill for Vehicle: ${currentVehicleNumber}`
            });
            console.log("PDF Shared successfully.");
        } else {
            // Fallback: Trigger WhatsApp deep link pointing to the bill download page
            triggerWhatsAppFallback();
        }
    } catch (e) {
        console.error("Native sharing failed. Attempting WhatsApp redirect fallback.", e);
        triggerWhatsAppFallback();
    }
}

// WhatsApp redirect fallback if Native file sharing is blocked or unsupported
function triggerWhatsAppFallback() {
    // Generate text message
    const msgText = `Hello, please check your invoice details for Vehicle: ${currentVehicleNumber}.\n\nDownload PDF Invoice here:\n${window.location.origin}/api/bills/${currentBillId}/pdf`;
    const whatsappUrl = `https://wa.me/91${currentCustomerMobile}?text=${encodeURIComponent(msgText)}`;
    
    // Automatically trigger PDF download first
    const link = document.createElement('a');
    link.href = `/api/bills/${currentBillId}/pdf`;
    link.download = `${currentBillNumber}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Open WhatsApp in new tab
    setTimeout(() => {
        window.open(whatsappUrl, '_blank');
    }, 800);
}

// Reset Billing Form
function resetForm() {
    document.getElementById('billing-form').reset();
    document.getElementById('items-container').innerHTML = '';
    
    // Reset values
    document.getElementById('discount-input').value = 0;
    document.getElementById('tax-input').value = 0;
    
    // Reset state
    itemCounter = 0;
    currentBillId = null;
    currentBillNumber = null;
    currentCustomerMobile = null;
    currentVehicleNumber = null;
    
    // Reinit Form
    initDate();
    fetchNextBillNumber();
    addParticularRow();
    
    // Switch Screen back
    document.getElementById('success-container').classList.add('hidden');
    document.getElementById('form-container').classList.remove('hidden');
}

// Handle Logout
async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login.html';
    } catch (e) {
        window.location.href = '/login.html';
    }
}
