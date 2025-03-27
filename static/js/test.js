document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const testForm = document.getElementById('test-form');
    const modelSelect = document.getElementById('model-select');
    const testNote = document.getElementById('test-note');
    const extractionPrompt = document.getElementById('extraction-prompt');
    const runExtractionBtn = document.getElementById('run-extraction-btn');
    const resultsContainer = document.getElementById('results-container');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const entityTemplate = document.getElementById('entity-template');
    
    // Theme Management
    function initTheme() {
        // Check for saved theme preference or use preferred color scheme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.body.setAttribute('data-theme', savedTheme);
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.setAttribute('data-theme', 'dark');
        }
    }
    
    function toggleTheme() {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }
    
    // API Calls
    async function runExtraction(provider, note, prompt) {
        try {
            const response = await fetch('/api/test/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: provider,
                    note: note,
                    prompt: prompt
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error running extraction:', error);
            throw error;
        }
    }
    
    // UI Rendering
    function renderResults(result) {
        resultsContainer.innerHTML = '';
        
        if (result.error) {
            // Show error message
            resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h5><i class="bi bi-exclamation-triangle"></i> Fehler</h5>
                    <p>${result.error}</p>
                </div>
            `;
            return;
        }
        
        // Show raw response
        const rawResponseDiv = document.createElement('div');
        rawResponseDiv.className = 'mb-4';
        rawResponseDiv.innerHTML = `
            <h5>Rohantwort vom LLM</h5>
            <pre class="bg-light p-3 rounded">${escapeHtml(result.raw_response)}</pre>
        `;
        resultsContainer.appendChild(rawResponseDiv);
        
        // Show extracted entities
        const entitiesDiv = document.createElement('div');
        entitiesDiv.className = 'mb-4';
        
        if (!result.entities || result.entities.length === 0) {
            entitiesDiv.innerHTML = `
                <h5>Extrahierte Entitäten</h5>
                <div class="alert alert-warning">
                    <p>Keine Entitäten extrahiert.</p>
                </div>
            `;
        } else {
            entitiesDiv.innerHTML = `
                <h5>Extrahierte Entitäten (${result.entities.length})</h5>
                <div class="entity-container mb-3"></div>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Typ</th>
                            <th>Label</th>
                            <th>Farbe</th>
                        </tr>
                    </thead>
                    <tbody id="entities-table-body"></tbody>
                </table>
            `;
            
            const entityContainer = entitiesDiv.querySelector('.entity-container');
            const tableBody = entitiesDiv.querySelector('#entities-table-body');
            
            result.entities.forEach(entity => {
                // Add entity badge
                const entityElement = document.importNode(entityTemplate.content, true);
                const entityBadge = entityElement.querySelector('.entity-badge');
                
                // Set badge style
                entityBadge.style.backgroundColor = entity.color;
                
                // Set label text
                entityElement.querySelector('.entity-label').textContent = entity.label;
                
                entityContainer.appendChild(entityElement);
                
                // Add table row
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${entity.type}</td>
                    <td>${entity.label}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="color-preview me-2" style="background-color: ${entity.color}"></div>
                            ${entity.color}
                        </div>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }
        
        resultsContainer.appendChild(entitiesDiv);
        
        // Add JSON representation
        const jsonDiv = document.createElement('div');
        jsonDiv.innerHTML = `
            <h5>JSON-Darstellung</h5>
            <pre class="bg-light p-3 rounded">${JSON.stringify(result.entities, null, 2)}</pre>
        `;
        resultsContainer.appendChild(jsonDiv);
    }
    
    // Helper function to escape HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    // Event Handlers
    async function handleFormSubmit(event) {
        event.preventDefault();
        
        // Get form values
        const provider = modelSelect.value;
        const note = testNote.value.trim();
        const prompt = extractionPrompt.value.trim();
        
        // Validate
        if (!note) {
            alert('Bitte geben Sie einen Text für die Extraktion ein.');
            return;
        }
        
        if (!prompt) {
            alert('Bitte geben Sie einen Prompt für die Extraktion ein.');
            return;
        }
        
        // Show loading state
        runExtractionBtn.disabled = true;
        runExtractionBtn.innerHTML = '<i class="bi bi-hourglass"></i> Verarbeite...';
        
        resultsContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border mb-3" role="status">
                    <span class="visually-hidden">Lädt...</span>
                </div>
                <p>Extrahiere Entitäten mit ${provider}...</p>
            </div>
        `;
        
        try {
            // Run extraction
            const result = await runExtraction(provider, note, prompt);
            
            // Render results
            renderResults(result);
            
        } catch (error) {
            console.error('Error:', error);
            
            // Show error message
            resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h5><i class="bi bi-exclamation-triangle"></i> Fehler</h5>
                    <p>Bei der Extraktion ist ein Fehler aufgetreten: ${error.message || 'Unbekannter Fehler'}</p>
                </div>
            `;
        } finally {
            // Reset button
            runExtractionBtn.disabled = false;
            runExtractionBtn.innerHTML = '<i class="bi bi-play-fill"></i> Extraktion starten';
        }
    }
    
    // Add CSS for color preview
    function addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .color-preview {
                width: 20px;
                height: 20px;
                border-radius: 3px;
                border: 1px solid #ccc;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Initialize
    function initialize() {
        initTheme();
        addStyles();
        
        // Set up event listeners
        themeToggleBtn.addEventListener('click', toggleTheme);
        testForm.addEventListener('submit', handleFormSubmit);
    }
    
    // Start the application
    initialize();
});
