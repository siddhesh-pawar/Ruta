// main.js
document.addEventListener('DOMContentLoaded', () => {

    /*** Auto-dismiss alerts after 5 seconds ***/
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    });

    /*** Form validation and submit button loading state ***/
    document.querySelectorAll('form').forEach(form => {

        // Validation
        form.addEventListener('submit', e => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            } else {
                // Add loading state to submit button
                const button = form.querySelector('button[type="submit"]');
                if (button) {
                    button.disabled = true;
                    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
                }
            }
            form.classList.add('was-validated');
        });

    });

    /*** Handle Tally form messages ***/
    if (window.location.pathname.includes('tally-form')) {
        window.addEventListener('message', e => {
            if (e.origin === 'https://tally.so') {
                console.log('Tally form event:', e.data);
            }
        });
    }

    /*** PWA-like navigation enhancement (future service worker) ***/
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            // Future: Register service worker for offline functionality
        });
    }

    /*** Smooth scroll for anchor links ***/
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', e => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

});
