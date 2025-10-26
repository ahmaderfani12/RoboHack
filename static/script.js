const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const responseArea = document.getElementById('responseArea');
const loading = document.getElementById('loading');

// Small typing animation for responses
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
async function typeText(el, text, speed = 18) {
    el.textContent = '';
    for (let i = 0; i < text.length; i++) {
        el.textContent += text[i];
        await sleep(speed);
    }
}

// Handle search submission
async function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    // Clear the input immediately
    searchInput.value = '';

    // Show loading state
    loading.classList.add('show');
    responseArea.classList.remove('show');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: query })
        });

        const data = await response.json();
        loading.classList.remove('show');

        if (data.success) {
            // responseArea.classList.add('show');
            // Animate the machine's reply with typing effect
            console.log('Response:', data.response);
            // await typeText(responseArea, data.response || '...');
        } else {
            // responseArea.classList.add('show');
            // await typeText(responseArea, 'Error: ' + (data.error || 'Something went wrong'));
        }
    } catch (error) {
        loading.classList.remove('show');
        responseArea.classList.add('show');
        await typeText(responseArea, 'Error: Could not connect to server');
        console.error('Error:', error);
    }
}

// Button click event
searchButton.addEventListener('click', handleSearch);

// Enter key event
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSearch();
});

// Focus on input when page loads
searchInput?.focus();