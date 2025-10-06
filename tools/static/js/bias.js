// js script for the bias_correction.html file

document.addEventListener('DOMContentLoaded', function() {
    // --- Function to update file name display ---
    function updateFileName(inputId, displayId) {
        const inputElement = document.getElementById(inputId);
        const displayElement = document.getElementById(displayId);
        if (inputElement && displayElement) {
            inputElement.addEventListener('change', function(e) {
                const fileName = e.target.files[0] ? e.target.files[0].name : 'No file selected';
                displayElement.textContent = fileName;
            });
        }
    }

    // Apply file name update to both inputs
    updateFileName('observations-file', 'observations-file-name');
    updateFileName('remote-sensing-file', 'remote-sensing-file-name');

    // --- Method card selection ---
    const methodCards = document.querySelectorAll('.method-card');
    const selectedMethodInput = document.getElementById('selected-method-input'); // Get hidden input

    methodCards.forEach(card => {
        card.addEventListener('click', function() {
            methodCards.forEach(c => c.classList.remove('selected')); // Deselect all
            this.classList.add('selected'); // Select clicked
            if (selectedMethodInput) {
                 selectedMethodInput.value = this.dataset.method; // *** UPDATE hidden input value ***
            }
        });
    });

    // --- Form submission (optional enhancements like loading state) ---
    const biasForm = document.getElementById('bias-correction-form');
    if (biasForm) {
        biasForm.addEventListener('submit', function(e) {
            // You can add code here to show a loading indicator
            console.log('Form is being submitted to the server...');
            const submitButton = biasForm.querySelector('button[type="submit"]');
            if(submitButton){
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            }
            // Allow default form submission to proceed
        });
    }
});