// js script for the water_levels.html file

document.addEventListener('DOMContentLoaded', () => {
    const predictForm = document.getElementById('predictionControlForm');
    if (predictForm) {
        predictForm.addEventListener('submit', event => {
            event.preventDefault(); // Prevent default form submission

            const payload = {
                // select_variable: document.getElementById('select_variable').value,
                reference_start: document.getElementById('reference-start').value,
                reference_end: document.getElementById('reference-end').value
                // horizon: document.getElementById('forecastHorizon').value
            };

            fetch('/levels/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken() // Ensure CSRF token is provided
                },
                body: JSON.stringify(payload)
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("Response from Django:", data);
                    if (data.plot_base64) {
                        const chartContainer = document.querySelector('.chart-container');
                        chartContainer.innerHTML = `<img src="data:image/png;base64,${data.plot_base64}" alt="Prediction Chart" class="img-fluid" style="max-height: 350px;">`;
                    } else if (data.error) {
                        console.error("Error from server:", data.error);
                    }
                })
                .catch(error => console.error("Error:", error));
        });
    }
});

function getCSRFToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return csrfToken;
}



