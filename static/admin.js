// Global State
let currentBills = [];

// Initialize Dashboard
window.addEventListener('DOMContentLoaded', () => {
    checkAdminAuth();
    loadStats();
    loadBills();
    
    // Attach Event Listeners
    document.getElementById('filter-form').addEventListener('submit', (e) => {
        e.preventDefault();
        loadBills();
    });
    
    document.getElementById('clear-filters-btn').addEventListener('click', () => {
        document.getElementById('filter-search').value = '';
        document.getElementById('filter-start').value = '';
        document.getElementById('filter-end').value = '';
        loadBills();
    });
    
    document.getElementById('export-csv-btn').addEventListener('click', handleCSVExport);
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
});

// Admin Authentication Guard
async function checkAdminAuth() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if (!data.logged_in || data.role !== 'admin') {
            window.location.href = '/admin-login.html';
        }
    } catch (e) {
        window.location.href = '/admin-login.html';
    }
}

// Load revenue and count stats
async function loadStats() {
    try {
        const res = await fetch('/api/admin/stats');
        if (res.ok) {
            const stats = await res.json();
            document.getElementById('stat-revenue').innerText = `₹${stats.total_revenue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            document.getElementById('stat-bills').innerText = stats.total_bills;
            document.getElementById('stat-average').innerText = `₹${stats.average_ticket.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    } catch (e) {
        console.error("Error loading stats", e);
    }
}

// Load and filter bills list
async function loadBills() {
    const search = document.getElementById('filter-search').value.trim();
    const start_date = document.getElementById('filter-start').value;
    const end_date = document.getElementById('filter-end').value;
    
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    try {
        const res = await fetch(`/api/admin/bills?${params.toString()}`);
        if (res.ok) {
            currentBills = await res.json();
            renderBillsTable(currentBills);
        }
    } catch (e) {
        console.error("Error loading bills", e);
    }
}

// Render dynamic rows in Bills list table
function renderBillsTable(bills) {
    const tbody = document.getElementById('bills-table-body');
    const emptyState = document.getElementById('empty-state');
    tbody.innerHTML = '';
    
    if (!bills || bills.length === 0) {
        emptyState.classList.remove('hidden');
        return;
    }
    emptyState.classList.add('hidden');
    
    bills.forEach(bill => {
        // Format Date
        const dateParts = bill.bill_date.split('-');
        const formattedDate = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
        
        const rowHTML = `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="py-4 px-6 font-bold text-[#0C54A0]">${bill.bill_number}</td>
                <td class="py-4 px-6 font-medium text-slate-500">${formattedDate}</td>
                <td class="py-4 px-6">
                    <div class="font-bold text-slate-800">${bill.customer_name}</div>
                    <button 
                        onclick="showCustomerHistory(${bill.bill_id})"
                        class="text-xs text-[#0C54A0] hover:underline font-semibold mt-0.5 flex items-center"
                    >
                        <i class="fa-solid fa-phone mr-1"></i> ${bill.customer_mobile}
                    </button>
                </td>
                <td class="py-4 px-6">
                    <div class="font-bold text-slate-800">${bill.vehicle_number}</div>
                    <button 
                        onclick="showVehicleHistory(${bill.bill_id})"
                        class="text-xs text-purple-600 hover:underline font-semibold mt-0.5 flex items-center"
                    >
                        <i class="fa-solid fa-car-side mr-1"></i> ${bill.vehicle_model || 'Unknown model'}
                    </button>
                </td>
                <td class="py-4 px-6 font-semibold text-slate-600">${bill.km.toLocaleString('en-IN')} km</td>
                <td class="py-4 px-6 font-bold text-right text-slate-800">₹${bill.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td class="py-4 px-6">
                    <div class="flex items-center justify-center space-x-2">
                        <a 
                            href="/api/bills/${bill.bill_id}/pdf" 
                            target="_blank"
                            class="bg-[#0C54A0] hover:bg-blue-800 text-white text-xs font-bold py-2 px-3 rounded-lg flex items-center transition-colors shadow-sm"
                        >
                            <i class="fa-solid fa-file-pdf mr-1"></i> View PDF
                        </a>
                    </div>
                </td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', rowHTML);
    });
}

// Fetch and display customer history in modal
async function showCustomerHistory(billId) {
    const bill = currentBills.find(b => b.bill_id === billId);
    if (!bill || !bill.customer_id) return;
    
    try {
        const res = await fetch(`/api/admin/customers/${bill.customer_id}/history`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('history-modal-title').innerText = `Customer History - ${data.customer.name}`;
            
            const infoCard = document.getElementById('history-info-card');
            infoCard.innerHTML = `
                <div><span class="font-bold text-slate-500">Name:</span> <span class="font-semibold text-slate-800">${data.customer.name}</span></div>
                <div><span class="font-bold text-slate-500">Mobile:</span> <span class="font-semibold text-slate-800">${data.customer.mobile}</span></div>
                <div class="col-span-2"><span class="font-bold text-slate-500">Address:</span> <span class="font-semibold text-slate-800">${data.customer.address || 'N/A'}</span></div>
            `;
            
            const historyTbody = document.getElementById('history-table-body');
            historyTbody.innerHTML = '';
            
            if (data.bills && data.bills.length > 0) {
                data.bills.forEach(b => {
                    const row = `
                        <tr class="hover:bg-slate-50">
                            <td class="py-2.5 px-4 font-bold text-[#0C54A0]">${b.bill_number}</td>
                            <td class="py-2.5 px-4 text-slate-600">${b.bill_date}</td>
                            <td class="py-2.5 px-4 text-slate-700 font-medium">${b.vehicle_number}</td>
                            <td class="py-2.5 px-4 text-right font-bold text-slate-800">₹${b.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        </tr>
                    `;
                    historyTbody.insertAdjacentHTML('beforeend', row);
                });
            } else {
                historyTbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-400">No previous bills found.</td></tr>`;
            }
            
            document.getElementById('history-modal').classList.remove('hidden');
        }
    } catch (e) {
        console.error("Error loading customer history", e);
    }
}

// Fetch and display vehicle history in modal
async function showVehicleHistory(billId) {
    const bill = currentBills.find(b => b.bill_id === billId);
    if (!bill || !bill.vehicle_id) return;
    
    try {
        const res = await fetch(`/api/admin/vehicles/${bill.vehicle_id}/history`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('history-modal-title').innerText = `Vehicle History - ${data.vehicle.vehicle_number}`;
            
            const infoCard = document.getElementById('history-info-card');
            infoCard.innerHTML = `
                <div><span class="font-bold text-slate-500">Vehicle No:</span> <span class="font-semibold text-slate-800">${data.vehicle.vehicle_number}</span></div>
                <div><span class="font-bold text-slate-500">Model:</span> <span class="font-semibold text-slate-800">${data.vehicle.model || 'N/A'}</span></div>
                <div><span class="font-bold text-slate-500">Customer:</span> <span class="font-semibold text-slate-800">${data.vehicle.customer_name}</span></div>
                <div><span class="font-bold text-slate-500">Mobile:</span> <span class="font-semibold text-slate-800">${data.vehicle.customer_mobile}</span></div>
            `;
            
            const historyTbody = document.getElementById('history-table-body');
            historyTbody.innerHTML = '';
            
            if (data.bills && data.bills.length > 0) {
                data.bills.forEach(b => {
                    const row = `
                        <tr class="hover:bg-slate-50">
                            <td class="py-2.5 px-4 font-bold text-[#0C54A0]">${b.bill_number}</td>
                            <td class="py-2.5 px-4 text-slate-600">${b.bill_date}</td>
                            <td class="py-2.5 px-4 text-slate-700 font-medium">${b.customer_name}</td>
                            <td class="py-2.5 px-4 text-right font-bold text-slate-800">₹${b.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        </tr>
                    `;
                    historyTbody.insertAdjacentHTML('beforeend', row);
                });
            } else {
                historyTbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-400">No previous bills found.</td></tr>`;
            }
            
            document.getElementById('history-modal').classList.remove('hidden');
        }
    } catch (e) {
        console.error("Error loading vehicle history", e);
    }
}

// Close History Modal
function closeHistoryModal() {
    document.getElementById('history-modal').classList.add('hidden');
}

// Export CSV handler
function handleCSVExport() {
    const search = document.getElementById('filter-search').value.trim();
    const start_date = document.getElementById('filter-start').value;
    const end_date = document.getElementById('filter-end').value;
    
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    window.location.href = `/api/admin/export/csv?${params.toString()}`;
}

// Handle Logout
async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/admin-login.html';
    } catch (e) {
        window.location.href = '/admin-login.html';
    }
}
