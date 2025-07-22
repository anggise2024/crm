// Global JavaScript functions for the CRM Follow-up System

// Show alert function
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Manual update function
function manualUpdate() {
    if (!confirm('This will trigger a manual data update from Google Sheets. Continue?')) {
        return;
    }
    
    showAlert('Starting manual update...', 'info');
    
    fetch('/manual-update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Data updated successfully!', 'success');
            // Reload page after 2 seconds
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showAlert(data.message || 'Error updating data', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error updating data', 'danger');
    });
}

// Recreate database function
function recreateDatabase() {
    if (!confirm('WARNING: This will delete all data and recreate the database. This action cannot be undone. Continue?')) {
        return;
    }
    
    if (!confirm('Are you absolutely sure? All existing data will be lost!')) {
        return;
    }
    
    showAlert('Recreating database...', 'warning');
    
    fetch('/recreate-database', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Database recreated successfully!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showAlert(data.message || 'Error recreating database', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error recreating database', 'danger');
    });
}

// Delete all records function
function deleteAllRecords() {
    if (!confirm('WARNING: This will delete all follow-up records. This action cannot be undone. Continue?')) {
        return;
    }
    
    if (!confirm('Are you absolutely sure? All follow-up data will be lost!')) {
        return;
    }
    
    showAlert('Deleting all records...', 'warning');
    
    fetch('/delete-all-records', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message || 'All records deleted successfully!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showAlert(data.message || 'Error deleting records', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error deleting records', 'danger');
    });
}

// Form enhancement - auto-submit on filter change
document.addEventListener('DOMContentLoaded', function() {
    // Auto-submit forms on select change (for filters)
    const autoSubmitSelects = document.querySelectorAll('form select[name="crm"], form select[name="status"], form select[name="date"], form select[name="today_followup"]');
    autoSubmitSelects.forEach(select => {
        select.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });
    
    // Add loading state to buttons
    document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Loading...';
            this.disabled = true;
            
            // Re-enable after 5 seconds as fallback
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 5000);
        });
    });
});

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('id-ID');
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('id-ID');
}

// Export table data function
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    const csvContent = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(cell => {
            // Clean cell text and escape quotes
            const text = cell.textContent.trim().replace(/"/g, '""');
            return `"${text}"`;
        }).join(',');
    }).join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename || 'export.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Search enhancement
function highlightSearchTerm(searchTerm) {
    if (!searchTerm || searchTerm.length < 2) return;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const elements = document.querySelectorAll('td, .card-body');
    
    elements.forEach(element => {
        const text = element.textContent;
        if (regex.test(text)) {
            element.innerHTML = element.innerHTML.replace(regex, '<mark>$1</mark>');
        }
    });
}

// Initialize search highlighting if search query exists
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput && searchInput.value) {
        highlightSearchTerm(searchInput.value);
    }
});
