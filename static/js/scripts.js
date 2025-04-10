document.addEventListener('DOMContentLoaded', function() {
    
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    initPropertyImageSlider();
    
    initSearchFilterToggle();
    
    initStarRating();
    
    initPaymentForm();
    
    initSavedPropertyToggle();
    
    initAppointmentStatusUpdate();
    
    initPropertyDeleteConfirmation();
    
    initAdminUserDeleteConfirmation();
});

function initPropertyImageSlider() {
    const propertySliders = document.querySelectorAll('.property-images-slider');
    
    propertySliders.forEach(slider => {
        const images = slider.querySelectorAll('.property-image-item');
        const nextBtn = slider.querySelector('.slider-next');
        const prevBtn = slider.querySelector('.slider-prev');
        
        if (!images.length || !nextBtn || !prevBtn) return;
        
        let currentIndex = 0;
        
        showImage(currentIndex);
        
        nextBtn.addEventListener('click', function() {
            currentIndex = (currentIndex + 1) % images.length;
            showImage(currentIndex);
        });
        
        prevBtn.addEventListener('click', function() {
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            showImage(currentIndex);
        });
        
        function showImage(index) {
            images.forEach((img, i) => {
                img.style.display = i === index ? 'block' : 'none';
            });
        }
    });
}

function initSearchFilterToggle() {
    const filterToggleBtn = document.getElementById('filter-toggle-btn');
    const filterContainer = document.getElementById('filter-container');
    
    if (!filterToggleBtn || !filterContainer) return;
    
    filterToggleBtn.addEventListener('click', function() {
        filterContainer.classList.toggle('d-none');
        filterContainer.classList.toggle('d-block');
        
        const isExpanded = filterToggleBtn.getAttribute('aria-expanded') === 'true';
        filterToggleBtn.setAttribute('aria-expanded', !isExpanded);
        filterToggleBtn.textContent = isExpanded ? 'Show Filters' : 'Hide Filters';
    });
}

function initStarRating() {
    const ratingInputs = document.querySelectorAll('.rating-input');
    
    ratingInputs.forEach(input => {
        const stars = input.querySelectorAll('.rating-star');
        const ratingValue = input.querySelector('input[type="hidden"]');
        
        if (!stars.length || !ratingValue) return;
        
        stars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const rating = index + 1;
                ratingValue.value = rating;
                
                
                stars.forEach((s, i) => {
                    s.classList.remove('active');
                    if (i < rating) {
                        s.classList.add('active');
                    }
                });
            });
        });
    });
}

function initPaymentForm() {
    const paymentForm = document.getElementById('payment-form');
    
    if (!paymentForm) return;
    
    paymentForm.addEventListener('submit', function(e) {
        const cardNumber = document.getElementById('card-number');
        const expiryDate = document.getElementById('expiry-date');
        const cvv = document.getElementById('cvv');
        
        let isValid = true;
        
        if (!cardNumber.value.trim()) {
            showError(cardNumber, 'Card number is required');
            isValid = false;
        }
        
        if (!expiryDate.value.trim()) {
            showError(expiryDate, 'Expiration date is required');
            isValid = false;
        }
        
        if (!cvv.value.trim()) {
            showError(cvv, 'CVV is required');
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    });
    
    function showError(inputElement, message) {
        const formGroup = inputElement.closest('.mb-3');
        const error = document.createElement('div');
        error.className = 'text-danger mt-1';
        error.textContent = message;
        
        const existingError = formGroup.querySelector('.text-danger');
        if (existingError) {
            existingError.remove();
        }
        
        formGroup.appendChild(error);
        inputElement.classList.add('is-invalid');
    }
}

function initSavedPropertyToggle() {
    const saveButtons = document.querySelectorAll('.save-property-btn');
    
    saveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const isSaved = button.getAttribute('data-saved') === 'true';
            const icon = button.querySelector('i');
            
            if (icon) {
                if (isSaved) {
                    icon.classList.remove('fas');
                    icon.classList.add('far');
                    button.setAttribute('data-saved', 'false');
                } else {
                    icon.classList.remove('far');
                    icon.classList.add('fas');
                    button.setAttribute('data-saved', 'true');
                }
            }
        });
    });
}

function initAppointmentStatusUpdate() {
    const statusForms = document.querySelectorAll('.appointment-status-form');
    
    statusForms.forEach(form => {
        const select = form.querySelector('select[name="status"]');
        
        if (!select) return;
        
        select.addEventListener('change', function() {
            form.submit();
        });
    });
}

function initPropertyDeleteConfirmation() {
    const deleteButtons = document.querySelectorAll('.delete-property-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this property? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
}

function initAdminUserDeleteConfirmation() {
    const deleteButtons = document.querySelectorAll('.admin-delete-user-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this user? All associated data will be permanently removed.')) {
                e.preventDefault();
            }
        });
    });
}
