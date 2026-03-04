// ========== SIDEBAR FUNCTIONALITY ==========

// Get sidebar elements
const hamburger = document.getElementById("hamburger");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const closeSidebar = document.getElementById("closeSidebar");

// Function to open sidebar
function openSidebar() {
  sidebar.classList.remove("sidebar-closed");
  sidebar.classList.add("sidebar-open");
  overlay.classList.remove("hidden");
  document.body.style.overflow = "hidden"; // Prevent background scrolling
}

// Function to close sidebar
function closeSidebarFunc() {
  sidebar.classList.add("sidebar-closed");
  sidebar.classList.remove("sidebar-open");
  overlay.classList.add("hidden");
  document.body.style.overflow = ""; // Restore scrolling
}

// Event listeners for sidebar
hamburger.addEventListener("click", openSidebar);
closeSidebar.addEventListener("click", closeSidebarFunc);
overlay.addEventListener("click", closeSidebarFunc);

// Close sidebar with Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSidebarFunc();
});

// ========== FILTER TABS FUNCTIONALITY ==========

// Get filter elements
const filterTabs = document.querySelectorAll(".filter-tab");
const loanTableContainer = document.getElementById("loan-table-container");
const monthlyReleasesContainer = document.getElementById(
  "monthly-releases-container",
);
const monthlyCollectionsContainer = document.getElementById(
  "monthly-collections-container",
);
const loanRows = document.querySelectorAll(".loan-row");

// Add click event to each filter tab
filterTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    // Remove active class from all tabs
    filterTabs.forEach((t) => t.classList.remove("active"));
    // Add active class to clicked tab
    tab.classList.add("active");

    // Get filter type from data attribute
    const filter = tab.dataset.filter;

    // Hide all containers first
    loanTableContainer.classList.add("hidden");
    monthlyReleasesContainer.classList.add("hidden");
    monthlyCollectionsContainer.classList.add("hidden");

    // Show appropriate container based on filter
    if (filter === "monthly-releases") {
      monthlyReleasesContainer.classList.remove("hidden");
    } else if (filter === "monthly-collections") {
      monthlyCollectionsContainer.classList.remove("hidden");
    } else {
      loanTableContainer.classList.remove("hidden");

      // Filter loan rows by status
      loanRows.forEach((row) => {
        if (filter === "all") {
          row.style.display = ""; // Show all rows
        } else {
          // Show only rows matching the filter status
          if (row.dataset.status === filter) {
            row.style.display = "";
          } else {
            row.style.display = "none";
          }
        }
      });
    }
  });
});

// ========== LOAN APPLICATION MODAL ==========

// Get loan modal elements
let loanModal = null;
let openLoanModalButton = null;
let closeModalButton = null;
let loanPlans = {}; // Store loan plans data
let ebikePlans = {}; // Store ebike model data with their plans

// Wait for DOM to be ready
function initLoanModal() {
  loanModal = document.getElementById("loanModal");
  openLoanModalButton = document.getElementById("openLoanModalButton");
  closeModalButton = document.getElementById("closeModal");
  
  if (!loanModal || !openLoanModalButton || !closeModalButton) {
    console.error('Required loan modal elements not found');
    return;
  }

  // Open loan modal
  openLoanModalButton.addEventListener("click", async () => {
    console.log('Loan modal button clicked');
    loanModal.classList.remove("hidden");
    
    // Load borrowers and ebike models
    await loadBorrowers();
    await loadEbikeModels();
  });

  // Handle ebike model selection - populate loan plans and auto-fill amount
  const loanUnitSelect = document.getElementById("loan-unit");
  const loanTermSelect = document.getElementById("loan-term");
  const loanAmountInput = document.getElementById("loan-amount");
  const loanPlanDetails = document.getElementById("loan-plan-details");
  const planInterestDisplay = document.getElementById("plan-interest-display");
  const planPenaltyDisplay = document.getElementById("plan-penalty-display");

  if (loanUnitSelect) {
    loanUnitSelect.addEventListener("change", () => {
      const selectedModelId = loanUnitSelect.value;
      console.log('Selected ebike model ID:', selectedModelId);
      
      if (selectedModelId && ebikePlans[selectedModelId]) {
        const model = ebikePlans[selectedModelId];
        console.log('Selected model data:', model);
        
        // Auto-fill loan amount with SRP
        loanAmountInput.value = parseFloat(model.srp).toFixed(2);
        console.log('Auto-filled loan amount with SRP:', model.srp);
        
        // Populate loan plans for this ebike model
        populateLoanPlansByModel(selectedModelId);
        
        // Clear previous plan details
        loanPlanDetails.classList.add("hidden");
        loanTermSelect.value = '';
      } else {
        // Clear loan amount if no model selected
        loanAmountInput.value = '';
        loanTermSelect.innerHTML = '<option value="">Select loan term</option>';
        loanPlanDetails.classList.add("hidden");
      }
    });
  }
  // Handle loan plan selection
  if (loanTermSelect) {
    loanTermSelect.addEventListener("change", () => {
      // Loan plan details will be shown in the calculation modal
      // Just reset the main modal plan details display
      loanPlanDetails.classList.add("hidden");
    });
  }

  // Close loan modal
  closeModalButton.addEventListener("click", () => {
    loanModal.classList.add("hidden");
  });

  // Close modal when clicking outside
  loanModal.addEventListener("click", (e) => {
    if (e.target === loanModal) {
      loanModal.classList.add("hidden");
    }
  });
}

async function loadEbikeModels() {
  const loanUnitSelect = document.getElementById("loan-unit");
  if (!loanUnitSelect) {
    console.error('Loan unit select element not found');
    return;
  }

  try {
    console.log('Fetching ebike models from /api/ebike-models/');
    
    const response = await fetch("/api/ebike-models/", {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      credentials: 'same-origin'
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('Ebike models response:', data);

    let models = [];
    if (Array.isArray(data)) {
      models = data;
    } else if (data.results && Array.isArray(data.results)) {
      models = data.results;
    }

    // Clear existing options
    loanUnitSelect.innerHTML = '<option value="">Select Unit</option>';

    if (models.length === 0) {
      const noOption = document.createElement('option');
      noOption.value = '';
      noOption.disabled = true;
      noOption.textContent = 'No ebike models available';
      loanUnitSelect.appendChild(noOption);
      console.warn('No ebike models returned from API');
      return;
    }

    // Add all ebike models
    models.forEach((model) => {
      console.log('Processing ebike model:', model);
      
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = model.name;
      loanUnitSelect.appendChild(option);
      
      // Store model data for later use
      ebikePlans[model.id] = {
        id: model.id,
        name: model.name,
        srp: model.srp,
        downpayment: model.downpayment,
        installment_6_months: model.installment_6_months,
        installment_12_months: model.installment_12_months,
        installment_15_months: model.installment_15_months,
        installment_18_months: model.installment_18_months,
        installment_24_months: model.installment_24_months
      };
      
      console.log(`Added ebike model: ${model.name} (SRP: ₱${model.srp})`);
    });

    console.log('Successfully loaded all ebike models');
  } catch (error) {
    console.error('Error loading ebike models:', error);
  }
}

function populateLoanPlansByModel(modelId) {
  const loanTermSelect = document.getElementById("loan-term");
  if (!loanTermSelect) {
    console.error('Loan term select element not found');
    return;
  }

  const model = ebikePlans[modelId];
  if (!model) {
    console.error('Model not found in ebikePlans:', modelId);
    return;
  }

  // Define available installment months
  const availableMonths = [6, 12, 15, 18, 24];
  
  // Clear existing options
  loanTermSelect.innerHTML = '<option value="">Select loan term</option>';

  // Add available plans for this model
  availableMonths.forEach(months => {
    const installmentField = `installment_${months}_months`;
    const amount = model[installmentField];
    
    // Only add option if the model has this installment plan
    if (amount !== null && amount !== undefined && amount !== '') {
      const option = document.createElement('option');
      option.value = months;
      option.textContent = `${months} Months`;
      loanTermSelect.appendChild(option);
      console.log(`Added loan plan option for ${months} months: ₱${amount}`);
    }
  });

  console.log(`Populated loan plans for model: ${model.name}`);
}

async function loadBorrowers() {
  const borrowerSelect = document.getElementById("loan-borrower");
  if (!borrowerSelect) {
    console.error('Borrower select element not found');
    return;
  }
  
  // Set initial loading state
  borrowerSelect.innerHTML = '<option value="">Loading borrowers...</option>';
  borrowerSelect.disabled = true;
  
  try {
    console.log('Fetching borrowers from /api/borrowers-json/');
    
    const response = await fetch("/api/borrowers-json/", {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      credentials: 'same-origin'
    });
    
    console.log('Fetch response status:', response.status, response.statusText);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Parsed response:', data);
    
    if (!data.results) {
      throw new Error('Response missing "results" field');
    }
    
    const borrowers = Array.isArray(data.results) ? data.results : [];
    console.log('Number of borrowers:', borrowers.length);
    
    // Clear and enable the select
    borrowerSelect.innerHTML = '';
    borrowerSelect.disabled = false;
    
    // Add default option
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select a borrower...';
    borrowerSelect.appendChild(defaultOption);
    
    if (borrowers.length === 0) {
      const noOption = document.createElement('option');
      noOption.value = '';
      noOption.disabled = true;
      noOption.textContent = 'No borrowers available';
      borrowerSelect.appendChild(noOption);
      console.warn('No borrowers returned from API');
      return;
    }
    
    // Add all borrowers
    borrowers.forEach((borrower, index) => {
      console.log(`Processing borrower ${index}:`, borrower);
      
      const option = document.createElement('option');
      option.value = borrower.id;
      
      const firstName = borrower.first_name ? borrower.first_name.trim() : '';
      const lastName = borrower.last_name ? borrower.last_name.trim() : '';
      const fullName = [firstName, lastName].filter(Boolean).join(' ');
      
      option.textContent = fullName || `Borrower #${borrower.id}`;
      borrowerSelect.appendChild(option);
      console.log(`Added option: "${option.textContent}" (ID: ${borrower.id})`);
    });
    
    console.log('Successfully loaded all borrowers');
    
  } catch (error) {
    console.error('Error loading borrowers:', error);
    borrowerSelect.innerHTML = '<option value="">Error: ' + error.message + '</option>';
    borrowerSelect.disabled = true;
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  console.log('DOM still loading, waiting for DOMContentLoaded...');
  document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded fired, initializing loan modal');
    initLoanModal();
  });
} else {
  console.log('DOM already loaded, initializing loan modal immediately');
  initLoanModal();
}

// ========== PAYMENT SCHEDULE MODAL ==========

// Get payment schedule modal elements
const viewPaymentScheduleButtons = document.querySelectorAll(
  ".viewPaymentScheduleBtn",
);
const paymentScheduleModal = document.getElementById("paymentScheduleModal");
const closePaymentScheduleModalButton = document.getElementById(
  "closePaymentScheduleModal",
);
const paymentScheduleTableBody = document.querySelector(
  "#paymentScheduleModal tbody"
);

// Function to fetch and display payment schedule
async function fetchAndShowPaymentSchedule(loanId) {
  try {
    const response = await fetch(`/api/loans/${loanId}/`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const loanData = await response.json();
    
    // Clear existing rows
    paymentScheduleTableBody.innerHTML = '';
    
    // Populate schedule from payment_schedules data
    if (loanData.payment_schedules && loanData.payment_schedules.length > 0) {
      loanData.payment_schedules.forEach((schedule) => {
        const row = document.createElement('tr');
        const statusClass = schedule.status === 'PAID' ? 'bg-green-50/50' : 'bg-yellow-50/50';
        const statusIcon = schedule.status === 'PAID' 
          ? '<i class="text-green-500 fas fa-check-circle"></i>'
          : '<i class="text-yellow-500 fas fa-clock"></i>';
        
        row.className = `text-gray-800 border-b hover:${statusClass}`;
        row.innerHTML = `
          <td class="px-3 py-2">
            <div class="flex items-center gap-2">
              ${statusIcon}
            </div>
          </td>
          <td class="px-3 py-2 font-medium">${new Date(schedule.due_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
          <td class="px-3 py-2 font-bold text-right">₱ ${parseFloat(schedule.amount).toFixed(2)}</td>
        `;
        paymentScheduleTableBody.appendChild(row);
      });
    } else {
      paymentScheduleTableBody.innerHTML = '<tr><td colspan="3" class="px-3 py-3 text-center text-gray-500">No schedule available</td></tr>';
    }
    
    // Show the modal
    paymentScheduleModal.classList.remove("hidden");
  } catch (error) {
    console.error('Error fetching payment schedule:', error);
    alert('Failed to load payment schedule. Please try again.');
  }
}

// Function to show payment schedule modal
function showPaymentScheduleModal() {
  paymentScheduleModal.classList.remove("hidden");
}

// Function to hide payment schedule modal
function hidePaymentScheduleModal() {
  paymentScheduleModal.classList.add("hidden");
  if (actionMenu) {
    actionMenu.classList.add("hidden"); // Also hide action menu
  }
}

// Add click event to all "View Payment Schedule" buttons
viewPaymentScheduleButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const loanId = button.getAttribute("data-loan-id");
    if (loanId) {
      await fetchAndShowPaymentSchedule(loanId);
    }
  });
});

// Close button event
if (closePaymentScheduleModalButton) {
  closePaymentScheduleModalButton.addEventListener(
    "click",
    hidePaymentScheduleModal,
  );
}

// Close when clicking outside modal
if (paymentScheduleModal) {
  paymentScheduleModal.addEventListener("click", (e) => {
    if (e.target === paymentScheduleModal) {
      hidePaymentScheduleModal();
    }
  });
}

// ========== CALCULATION MODAL ==========

// Get calculation modal elements
const openCalcModalButton = document.getElementById("open-calc-modal");
const calcModal = document.getElementById("calculation-modal");
const closeCalcModalButton = document.getElementById("closeCalcModal");
const calcCancelButton = document.getElementById("calc-cancel-button");
const calcApplyButton = document.getElementById("calc-apply-button");

// Function to show calculation modal
const showCalcModal = () => {
  calcModal.classList.remove("hidden");
};

// Function to hide calculation modal
const hideCalcModal = () => {
  calcModal.classList.add("hidden");
};

// Open calculation modal
if (openCalcModalButton) {
  openCalcModalButton.addEventListener("click", (e) => {
    e.preventDefault();
    
    // Get form values
    const borrowerId = document.getElementById("loan-borrower").value;
    const modelId = parseInt(document.getElementById("loan-unit").value);
    const months = parseInt(document.getElementById("loan-term").value);
    const amount = parseFloat(document.getElementById("loan-amount").value);

    // Validate inputs
    if (!borrowerId || !modelId || !months || !amount || amount <= 0) {
      alert("Please fill in all fields (borrower, model unit, loan plan, and amount)");
      return;
    }

    // Get the selected ebike model
    const modelData = ebikePlans[modelId];
    if (!modelData) {
      alert("Invalid ebike model selected");
      return;
    }

    // Get the installment amount for the selected months from the model
    const monthlyInstallment = modelData['installment_' + months + '_months'];
    if (monthlyInstallment === null || monthlyInstallment === undefined) {
      alert("This installment plan is not available for the selected model");
      return;
    }

    // For calculation, use the monthly installment from the model
    const monthlyPayment = parseFloat(monthlyInstallment);
    const totalPayable = monthlyPayment * months;
    
    // Down payment from the model
    const downPayment = parseFloat(modelData.downpayment);
    
    // Penalty amount - use 5% of monthly payment as a reasonable default
    const monthlyPenalty = monthlyPayment * 0.05;

    // Calculate first payment date (30 days after loan creation)
    const today = new Date();
    const firstPaymentDate = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
    const dateString = firstPaymentDate.toLocaleDateString('en-PH', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    // Update calculation display
    document.getElementById("calc-total-payable").textContent = totalPayable.toFixed(2);
    document.getElementById("calc-monthly-amount").textContent = monthlyPayment.toFixed(2);
    document.getElementById("calc-penalty-amount").textContent = monthlyPenalty.toFixed(2);
    document.getElementById("calc-first-payment-date").textContent = dateString;
    
    // Update loan plan details in calculation modal
    document.getElementById("calc-model-name").textContent = modelData.name;
    document.getElementById("calc-loan-term").textContent = `${months} Months`;
    document.getElementById("calc-monthly-installment").textContent = monthlyPayment.toFixed(2);
    document.getElementById("calc-down-payment").textContent = downPayment.toFixed(2);

    showCalcModal();
    console.log('Calculation details:', {
      model: modelData.name,
      amount,
      months,
      monthlyPayment,
      totalPayable,
      downPayment,
      monthlyPenalty,
      firstPaymentDate: dateString
    });
  });
}

// Close calculation modal - X button
if (closeCalcModalButton) {
  closeCalcModalButton.addEventListener("click", hideCalcModal);
}

// Close calculation modal - Cancel button
if (calcCancelButton) {
  calcCancelButton.addEventListener("click", hideCalcModal);
}

// Close when clicking outside modal
if (calcModal) {
  calcModal.addEventListener("click", (e) => {
    if (e.target === calcModal) {
      hideCalcModal();
    }
  });
}

// ========== SUCCESS MODAL ==========

// Get success modal elements
const successModal = document.getElementById("success-modal");
const successOkButton = document.getElementById("success-ok-button");
const successTitle = document.getElementById("success-title");
const successMessage = document.getElementById("success-message");
const successIconContainer = document.getElementById("success-icon-container");

/**
 * Show success modal with custom content
 * @param {string} title - Modal title
 * @param {string} message - Success message
 * @param {string} iconHtml - HTML for icon
 * @param {boolean} isLoanSuccess - Whether this is a loan approval success
 */
const showSuccessModal = (title, message, iconHtml, isLoanSuccess = false) => {
  successTitle.textContent = title;
  successMessage.textContent = message;
  successIconContainer.innerHTML = iconHtml;
  successModal.classList.remove("hidden");

  // If loan success, also close loan modal when clicking OK
  if (isLoanSuccess) {
    successOkButton.onclick = () => {
      hideSuccessModal();
      loanModal.classList.add("hidden");
      successOkButton.onclick = hideSuccessModal; // Reset onclick
    };
  } else {
    successOkButton.onclick = hideSuccessModal;
  }
};

// Function to hide success modal
const hideSuccessModal = () => {
  successModal.classList.add("hidden");
};

// OK button event
successOkButton.addEventListener("click", hideSuccessModal);

// Apply Loan Button - Create loan via API
if (calcApplyButton) {
  calcApplyButton.addEventListener("click", async () => {
    const borrowerId = document.getElementById("loan-borrower").value;
    const modelId = parseInt(document.getElementById("loan-unit").value);
    const loanAmount = document.getElementById("loan-amount").value;
    const loanTerm = document.getElementById("loan-term").value;

    if (!borrowerId || !modelId || !loanAmount || !loanTerm) {
      alert("Please fill in all required fields");
      return;
    }

    // Get the model data to get down payment
    const modelData = ebikePlans[modelId];
    if (!modelData) {
      alert("Invalid ebike model selected");
      return;
    }

    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      if (!csrfToken) {
        console.error('CSRF token not found in page');
      }

      // Calculate payment schedule date (30 days from today)
      const today = new Date();
      const paymentScheduleDate = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
      const dateString = paymentScheduleDate.toISOString().split('T')[0]; // YYYY-MM-DD format

      const payload = {
        borrower_id: borrowerId,
        ebike_model_id: modelId,
        amount: parseFloat(loanAmount),
        term: parseInt(loanTerm),
        down_payment: parseFloat(modelData.downpayment),
        payment_schedule_date: dateString  // First payment due 30 days after creation
      };
      
      console.log('Sending loan creation request with payload:', payload);

      const response = await fetch("/api/add-loan/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken || ''
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });

      console.log('Response status:', response.status, 'OK:', response.ok);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Response data:', data);

      if (data.status === 'success') {
        hideCalcModal();
        const loanTitle = "Loan Approved!";
        const loanMessage = `Loan #${data.loan_id} has been successfully created with amount ₱${data.loan_amount}. First payment is due on ${paymentScheduleDate.toLocaleDateString('en-PH')}`;
        const loanIcon = '<svg class="w-16 h-16 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';

        showSuccessModal(loanTitle, loanMessage, loanIcon, true);
        
        // Reload page after 2 seconds to show new loan
        setTimeout(() => location.reload(), 2000);
      } else {
        throw new Error(data.message || 'Failed to create loan');
      }
    } catch (error) {
      console.error('Error creating loan:', error);
      alert('Error creating loan: ' + error.message);
    }
  });
}

// ========== ACTION MENU (CONTEXT MENU) ==========

// Get action menu elements
const actionMenu = document.getElementById("actionMenu");
const sendActionTriggers = document.querySelectorAll(".send-action-trigger");
const actionButtons = document.querySelectorAll(".action-button");

// Track which send icon was clicked
let currentSendIcon = null;

/**
 * Show action menu near clicked icon
 * @param {Event} event - Click event
 */
const showActionMenu = (event) => {
  event.stopPropagation();
  hideActionMenu(); // Hide any existing menu first

  // Store reference to clicked icon
  currentSendIcon = event.currentTarget;
  const rect = currentSendIcon.getBoundingClientRect();

  // Position menu next to the icon
  actionMenu.style.top = `${rect.top + window.scrollY}px`;
  actionMenu.style.left = `${rect.left + rect.width + 10 + window.scrollX}px`;
  actionMenu.classList.remove("hidden");
};

// Function to hide action menu
const hideActionMenu = () => {
  actionMenu.classList.add("hidden");
  currentSendIcon = null;
};

// Add click event to all send action trigger icons
sendActionTriggers.forEach((icon) => {
  icon.addEventListener("click", showActionMenu);
});

// Handle action button clicks
actionButtons.forEach((button) => {
  button.addEventListener("click", (e) => {
    e.stopPropagation();

    // Get action type and data from current icon
    const action = button.dataset.action;
    const ref = currentSendIcon.dataset.ref;
    const date = currentSendIcon.dataset.date;
    let message = "";
    let title = "";
    let icon = "";

    // Set message based on action type
    if (action === "reminder") {
      message = `Reminder message successfully sent for the payment due on ${date}.`;
      title = "Reminder Sent";
      icon = '<i class="text-green-600 fa-4x fas fa-bell"></i>';
    } else if (action === "overdue") {
      message = `Overdue notice sent for loan #${ref}. The borrower has been notified.`;
      title = "Overdue Notice Sent";
      icon = '<i class="text-red-600 fa-4x fas fa-exclamation-triangle"></i>';
    } else if (action === "sms") {
      message = `SMS message successfully sent to the borrower's contact number.`;
      title = "SMS Sent";
      icon = '<i class="w-16 h-16 text-blue-600 fas fa-sms"></i>';
    }

    // Hide menu and show success modal
    hideActionMenu();
    showSuccessModal(title, message, icon);
  });
});

// Close action menu when clicking anywhere else on page
document.addEventListener("click", (e) => {
  if (
    !actionMenu.contains(e.target) &&
    !e.target.closest(".send-action-trigger")
  ) {
    hideActionMenu();
  }
});

// Close modals with Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    hideActionMenu();
    hideSuccessModal();
  }
});

// ========== AUTO-SELECT TAB FROM URL HASH ==========

window.addEventListener("DOMContentLoaded", () => {
  const hash = window.location.hash.substring(1); // Remove the # symbol

  if (hash) {
    const targetTab = document.querySelector(`[data-filter="${hash}"]`);

    if (targetTab) {
      targetTab.click();
    }
  }
});
