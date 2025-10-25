const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const responseArea = document.getElementById('responseArea');
const loading = document.getElementById('loading');

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
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: query })
        });
        
        const data = await response.json();
        
        // Hide loading
        loading.classList.remove('show');
        
        if (data.success) {
            // Display the response
            responseArea.textContent = data.response;
            responseArea.classList.add('show');
        } else {
            responseArea.textContent = 'Error: ' + (data.error || 'Something went wrong');
            responseArea.classList.add('show');
        }
    } catch (error) {
        loading.classList.remove('show');
        responseArea.textContent = 'Error: Could not connect to server';
        responseArea.classList.add('show');
        console.error('Error:', error);
    }
}

// Button click event
searchButton.addEventListener('click', handleSearch);

// Enter key event
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

// Optional: Focus on input when page loads
searchInput.focus();