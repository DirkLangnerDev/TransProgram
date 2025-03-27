document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const messagesContainer = document.getElementById('messages-container');
    const totalMessagesElement = document.getElementById('total-messages');
    const refreshButton = document.getElementById('refresh-btn');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const newMessageForm = document.getElementById('new-message-form');
    const newMessageDate = document.getElementById('new-message-date');
    const newMessageTime = document.getElementById('new-message-time');
    const newMessageText = document.getElementById('new-message-text');
    
    // Templates
    const dateGroupTemplate = document.getElementById('date-group-template');
    const messageTemplate = document.getElementById('message-template');
    const emptyStateTemplate = document.getElementById('empty-state-template');
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
    
    // Data Fetching
    async function fetchMessages() {
        try {
            const response = await fetch('/api/messages');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching messages:', error);
            return [];
        }
    }
    
    async function fetchStats() {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching stats:', error);
            return { total_messages: 0 };
        }
    }
    
    async function fetchMessageEntities(messageId) {
        try {
            const response = await fetch(`/api/messages/${messageId}/entities`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching entities for message ${messageId}:`, error);
            return [];
        }
    }
    
    async function fetchAllEntities() {
        try {
            const response = await fetch('/api/entities');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching all entities:', error);
            return [];
        }
    }
    
    async function updateEntity(entityId, data) {
        try {
            const response = await fetch(`/api/entities/${entityId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            return await response.json();
        } catch (error) {
            console.error(`Error updating entity ${entityId}:`, error);
            throw error;
        }
    }
    
    async function mergeEntities(entityIds, mergedEntity) {
        try {
            const response = await fetch('/api/entities/merge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    entity_ids: entityIds,
                    merged_entity: mergedEntity
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error merging entities:', error);
            throw error;
        }
    }
    
    async function extractEntities(messageId) {
        try {
            const response = await fetch(`/api/messages/${messageId}/extract-entities`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            return await response.json();
        } catch (error) {
            console.error(`Error extracting entities for message ${messageId}:`, error);
            throw error;
        }
    }
    
    // UI Rendering
    function formatDate(dateStr) {
        const date = new Date(dateStr);
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        return date.toLocaleDateString('de-DE', options);
    }
    
    // Date and Time Helpers
    function getCurrentDateTime() {
        const now = new Date();
        return {
            date: now.toISOString().split('T')[0], // YYYY-MM-DD
            time: now.toTimeString().split(' ')[0].substring(0, 5) // HH:MM
        };
    }
    
    function formatISODateTime(dateStr, timeStr) {
        // Combine date and time into ISO format: YYYY-MM-DDThh:mm:ss
        return `${dateStr}T${timeStr}:00`;
    }
    
    function parseISODateTime(isoString) {
        // Parse ISO datetime string into date and time components
        const date = new Date(isoString);
        return {
            date: date.toISOString().split('T')[0], // YYYY-MM-DD
            time: date.toTimeString().split(' ')[0].substring(0, 5) // HH:MM
        };
    }

    async function renderMessages(dateGroups) {
        messagesContainer.innerHTML = '';
        
        if (dateGroups.length === 0) {
            const emptyState = document.importNode(emptyStateTemplate.content, true);
            messagesContainer.appendChild(emptyState);
            return;
        }
        
        // Initialize entity edit modal
        initEntityModals();
        
        for (const group of dateGroups) {
            const dateGroup = document.importNode(dateGroupTemplate.content, true);
            const dateHeader = dateGroup.querySelector('.date-header');
            const messageList = dateGroup.querySelector('.message-list');
            
            dateHeader.textContent = formatDate(group.date);
            
            for (const message of group.messages) {
                const messageElement = document.importNode(messageTemplate.content, true);
                const messageCard = messageElement.querySelector('.message-card');
                
                // Store message data for editing
                messageCard.dataset.id = message.id;
                messageCard.dataset.timestamp = message.timestamp;
                messageCard.dataset.transcript = message.transcript;
                
                // Format timestamp for display (just the time part)
                messageElement.querySelector('.message-time').textContent = message.formatted_time;
                messageElement.querySelector('.message-id').textContent = `#${message.id}`;
                messageElement.querySelector('.message-text').textContent = message.transcript;
                
                // Set up edit button
                const editBtn = messageElement.querySelector('.edit-message-btn');
                editBtn.addEventListener('click', function() {
                    toggleEditMode(messageCard, true);
                });
                
                // Set up save button
                const saveBtn = messageElement.querySelector('.save-edit-btn');
                saveBtn.addEventListener('click', function() {
                    saveMessageEdit(messageCard);
                });
                
                // Set up cancel button
                const cancelBtn = messageElement.querySelector('.cancel-edit-btn');
                cancelBtn.addEventListener('click', function() {
                    toggleEditMode(messageCard, false);
                });
                
                // Set up extract entities button
                const extractBtn = messageElement.querySelector('.extract-entities-btn');
                extractBtn.addEventListener('click', async function() {
                    try {
                        extractBtn.disabled = true;
                        extractBtn.innerHTML = '<i class="bi bi-hourglass"></i> Extrahiere...';
                        
                        const result = await extractEntities(message.id);
                        
                        if (!result.success) {
                            // Show error message
                            alert(`Fehler: ${result.error || 'Unbekannter Fehler beim Extrahieren der Entitäten.'}`);
                            return;
                        }
                        
                        // Render the extracted entities
                        if (result.entities && result.entities.length > 0) {
                            renderEntitiesForMessage(messageCard, result.entities);
                        } else {
                            alert('Keine Entitäten gefunden. Möglicherweise ist der LLM-Dienst nicht erreichbar oder es wurden keine Entitäten erkannt.');
                        }
                    } catch (error) {
                        console.error('Error extracting entities:', error);
                        alert('Fehler beim Extrahieren der Entitäten: ' + (error.message || 'Unbekannter Fehler'));
                    } finally {
                        extractBtn.disabled = false;
                        extractBtn.innerHTML = '<i class="bi bi-tags"></i> Entitäten extrahieren';
                    }
                });
                
                messageList.appendChild(messageElement);
                
                // Load and render entities for this message
                loadEntitiesForMessage(messageCard);
            }
            
            messagesContainer.appendChild(dateGroup);
        }
    }
    
    async function loadEntitiesForMessage(messageCard) {
        const messageId = messageCard.dataset.id;
        const entityContainer = messageCard.querySelector('.entity-container');
        
        try {
            const entities = await fetchMessageEntities(messageId);
            renderEntitiesForMessage(messageCard, entities);
        } catch (error) {
            console.error(`Error loading entities for message ${messageId}:`, error);
            entityContainer.innerHTML = '<span class="text-muted">Fehler beim Laden der Entitäten</span>';
        }
    }
    
    function renderEntitiesForMessage(messageCard, entities) {
        const entityContainer = messageCard.querySelector('.entity-container');
        entityContainer.innerHTML = '';
        
        if (!entities || entities.length === 0) {
            return;
        }
        
        entities.forEach(entity => {
            const entityElement = document.importNode(entityTemplate.content, true);
            const entityBadge = entityElement.querySelector('.entity-badge');
            
            // Set entity data
            entityBadge.dataset.id = entity.id;
            entityBadge.dataset.type = entity.type;
            entityBadge.dataset.label = entity.label;
            entityBadge.dataset.color = entity.color;
            
            // Set badge style
            entityBadge.style.backgroundColor = entity.color;
            
            // Set label text
            entityElement.querySelector('.entity-label').textContent = entity.label;
            
            // Set up edit button
            const editBtn = entityElement.querySelector('.entity-edit-btn');
            editBtn.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent badge click
                openEntityEditModal(entity);
            });
            
            // Add click handler for the badge itself
            entityBadge.addEventListener('click', function() {
                // Filter messages by this entity (future feature)
                console.log(`Filter by entity: ${entity.label}`);
            });
            
            entityContainer.appendChild(entityElement);
        });
    }
    
    function initEntityModals() {
        // Entity Edit Modal
        const entityEditModal = new bootstrap.Modal(document.getElementById('entityEditModal'));
        const saveEntityBtn = document.getElementById('save-entity-btn');
        
        saveEntityBtn.addEventListener('click', async function() {
            const entityId = document.getElementById('entity-id').value;
            const entityType = document.getElementById('entity-type').value;
            const entityLabel = document.getElementById('entity-label').value;
            const entityColor = document.getElementById('entity-color').value;
            
            if (!entityLabel.trim()) {
                alert('Bitte geben Sie eine Bezeichnung ein.');
                return;
            }
            
            try {
                await updateEntity(entityId, {
                    type: entityType,
                    label: entityLabel,
                    color: entityColor
                });
                
                entityEditModal.hide();
                
                // Refresh data to show updated entities
                await refreshData();
                
            } catch (error) {
                console.error('Error saving entity:', error);
                alert('Fehler beim Speichern der Entität.');
            }
        });
        
        // Entity Merge Modal
        const entityMergeModal = new bootstrap.Modal(document.getElementById('entityMergeModal'));
        const mergeEntitiesBtn = document.getElementById('merge-entities-btn');
        
        mergeEntitiesBtn.addEventListener('click', async function() {
            const mergeList = document.getElementById('merge-entities-list');
            const selectedCheckboxes = mergeList.querySelectorAll('input[type="checkbox"]:checked');
            
            if (selectedCheckboxes.length < 2) {
                alert('Bitte wählen Sie mindestens zwei Entitäten aus.');
                return;
            }
            
            const entityIds = Array.from(selectedCheckboxes).map(cb => cb.value);
            const mergedType = document.getElementById('merged-entity-type').value;
            const mergedLabel = document.getElementById('merged-entity-label').value;
            const mergedColor = document.getElementById('merged-entity-color').value;
            
            if (!mergedLabel.trim()) {
                alert('Bitte geben Sie eine Bezeichnung für die zusammengeführte Entität ein.');
                return;
            }
            
            try {
                await mergeEntities(entityIds, {
                    type: mergedType,
                    label: mergedLabel,
                    color: mergedColor
                });
                
                entityMergeModal.hide();
                
                // Refresh data to show merged entities
                await refreshData();
                
            } catch (error) {
                console.error('Error merging entities:', error);
                alert('Fehler beim Zusammenführen der Entitäten.');
            }
        });
    }
    
    function openEntityEditModal(entity) {
        const entityId = document.getElementById('entity-id');
        const entityType = document.getElementById('entity-type');
        const entityLabel = document.getElementById('entity-label');
        const entityColor = document.getElementById('entity-color');
        
        entityId.value = entity.id;
        entityType.value = entity.type;
        entityLabel.value = entity.label;
        entityColor.value = entity.color;
        
        const modal = new bootstrap.Modal(document.getElementById('entityEditModal'));
        modal.show();
    }
    
    async function openEntityMergeModal() {
        const mergeList = document.getElementById('merge-entities-list');
        mergeList.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Lädt...</span></div>';
        
        try {
            const entities = await fetchAllEntities();
            
            if (entities.length < 2) {
                alert('Es müssen mindestens zwei Entitäten vorhanden sein, um sie zusammenzuführen.');
                return;
            }
            
            mergeList.innerHTML = '';
            
            entities.forEach(entity => {
                const checkbox = document.createElement('div');
                checkbox.className = 'form-check';
                checkbox.innerHTML = `
                    <input class="form-check-input" type="checkbox" value="${entity.id}" id="entity-${entity.id}">
                    <label class="form-check-label" for="entity-${entity.id}">
                        <span class="badge" style="background-color: ${entity.color}">${entity.label}</span>
                        <small class="text-muted">(${entity.type})</small>
                    </label>
                `;
                mergeList.appendChild(checkbox);
            });
            
            const modal = new bootstrap.Modal(document.getElementById('entityMergeModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading entities for merge:', error);
            alert('Fehler beim Laden der Entitäten.');
        }
    }
    
    function toggleEditMode(messageCard, isEditing) {
        const messageText = messageCard.querySelector('.message-text');
        const editControls = messageCard.querySelector('.edit-controls');
        const editBtn = messageCard.querySelector('.edit-message-btn');
        
        if (isEditing) {
            // Show edit controls
            editControls.style.display = 'block';
            editBtn.style.display = 'none';
            
            // Fill edit fields with current values
            const { date, time } = parseISODateTime(messageCard.dataset.timestamp);
            messageCard.querySelector('.edit-date').value = date;
            messageCard.querySelector('.edit-time').value = time;
            messageCard.querySelector('.edit-transcript').value = messageCard.dataset.transcript;
        } else {
            // Hide edit controls
            editControls.style.display = 'none';
            editBtn.style.display = 'inline-block';
        }
    }
    
    async function saveMessageEdit(messageCard) {
        const messageId = messageCard.dataset.id;
        const dateInput = messageCard.querySelector('.edit-date').value;
        const timeInput = messageCard.querySelector('.edit-time').value;
        const transcriptInput = messageCard.querySelector('.edit-transcript').value;
        
        // Validate inputs
        if (!dateInput || !timeInput || !transcriptInput.trim()) {
            alert('Bitte füllen Sie alle Felder aus.');
            return;
        }
        
        // Format timestamp
        const timestamp = formatISODateTime(dateInput, timeInput);
        
        try {
            const response = await fetch(`/api/messages/${messageId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    timestamp: timestamp,
                    transcript: transcriptInput
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const result = await response.json();
            
            // Check for warnings
            if (result.warning) {
                console.warn('Warning during entity extraction:', result.warning);
                alert(`Memo wurde aktualisiert, aber es gab ein Problem bei der Entitätsextraktion: ${result.warning}`);
            }
            
            // Update the message card with new values
            messageCard.dataset.timestamp = timestamp;
            messageCard.dataset.transcript = transcriptInput;
            
            // Update displayed text
            const timeObj = new Date(timestamp);
            messageCard.querySelector('.message-time').textContent = timeObj.toTimeString().split(' ')[0];
            messageCard.querySelector('.message-text').textContent = transcriptInput;
            
            // Exit edit mode
            toggleEditMode(messageCard, false);
            
            // Refresh data to ensure correct grouping by date
            await refreshData();
            
        } catch (error) {
            console.error('Error updating message:', error);
            alert('Fehler beim Speichern der Änderungen. Bitte versuchen Sie es erneut.');
        }
    }
    
    function updateStats(stats) {
        totalMessagesElement.textContent = `${stats.total_messages} Memos`;
    }
    
    // Initialize and load data
    async function initialize() {
        initTheme();
        
        // Set default date and time for new message form
        const { date, time } = getCurrentDateTime();
        newMessageDate.value = date;
        newMessageTime.value = time;
        
        // Load initial data
        await refreshData();
        
        // Set up event listeners
        themeToggleBtn.addEventListener('click', toggleTheme);
        refreshButton.addEventListener('click', refreshData);
        newMessageForm.addEventListener('submit', handleNewMessageSubmit);
    }
    
    async function handleNewMessageSubmit(event) {
        event.preventDefault();
        
        // Get form values
        const dateValue = newMessageDate.value;
        const timeValue = newMessageTime.value;
        const textValue = newMessageText.value.trim();
        
        // Validate
        if (!dateValue || !timeValue || !textValue) {
            alert('Bitte füllen Sie alle Felder aus.');
            return;
        }
        
        // Format timestamp
        const timestamp = formatISODateTime(dateValue, timeValue);
        
        try {
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    timestamp: timestamp,
                    transcript: textValue
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const result = await response.json();
            
            // Check for warnings
            if (result.warning) {
                console.warn('Warning during entity extraction:', result.warning);
                alert(`Memo wurde gespeichert, aber es gab ein Problem bei der Entitätsextraktion: ${result.warning}`);
            }
            
            // Clear form
            newMessageText.value = '';
            
            // Reset date and time to current
            const { date, time } = getCurrentDateTime();
            newMessageDate.value = date;
            newMessageTime.value = time;
            
            // Refresh data to show new message
            await refreshData();
            
        } catch (error) {
            console.error('Error creating message:', error);
            alert('Fehler beim Erstellen des Memos. Bitte versuchen Sie es erneut.');
        }
    }
    
    async function refreshData() {
        // Show loading state
        messagesContainer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <div class="spinner-border mb-3" role="status">
                    <span class="visually-hidden">Lädt...</span>
                </div>
                <p>Lade Memos...</p>
            </div>
        `;
        
        // Fetch data
        const [messages, stats] = await Promise.all([
            fetchMessages(),
            fetchStats()
        ]);
        
        // Update UI
        renderMessages(messages);
        updateStats(stats);
    }
    
    // Start the application
    initialize();
});
