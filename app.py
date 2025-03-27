import sqlite3
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import os
from pathlib import Path
import json

from llm_client import LLMClient
from config import Config

app = Flask(__name__)

# Get the extraction prompt from the LLM client
def get_extraction_prompt():
    """Get the extraction prompt used by the LLM client."""
    # Create a temporary LLM client to get the prompt
    temp_client = LLMClient()
    # Get the prompt by calling the private method
    # This is a bit of a hack, but it allows us to reuse the prompt
    return temp_client._create_extraction_prompt("").strip()

# Initialize configuration
config = Config()

# Initialize LLM client
def get_llm_client():
    """Get an LLM client based on current configuration."""
    llm_config = config.get_llm_config()
    provider = llm_config.get("provider", "ollama")
    provider_config = llm_config.get(provider, {})
    return LLMClient(provider=provider, config=provider_config)

def get_db_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect('transcripts.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/test')
def test_page():
    """Render the test page for entity extraction."""
    llm_config = config.get_llm_config()
    extraction_prompt = get_extraction_prompt()
    return render_template('test.html', llm_config=llm_config, extraction_prompt=extraction_prompt)

@app.route('/api/messages')
def get_messages():
    """API endpoint to get messages, optionally filtered by date."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, timestamp, transcript FROM messages"
    params = []
    
    # Add date filtering if provided
    if start_date and end_date:
        query += " WHERE timestamp BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    # Order by timestamp descending (newest first)
    query += " ORDER BY timestamp DESC"
    
    cursor.execute(query, params)
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Group messages by date for the calendar view
    grouped_messages = {}
    for message in messages:
        # Parse the ISO timestamp and format the date part as YYYY-MM-DD
        timestamp = datetime.fromisoformat(message['timestamp'])
        date_str = timestamp.strftime('%Y-%m-%d')
        
        # Add formatted time for display
        message['formatted_time'] = timestamp.strftime('%H:%M:%S')
        
        if date_str not in grouped_messages:
            grouped_messages[date_str] = []
        
        grouped_messages[date_str].append(message)
    
    # Convert to a list of date objects for the response
    result = [
        {
            'date': date,
            'messages': messages
        }
        for date, messages in sorted(grouped_messages.items(), reverse=True)
    ]
    
    return jsonify(result)

@app.route('/api/stats')
def get_stats():
    """API endpoint to get basic statistics about the messages."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) as count FROM messages")
    total_count = cursor.fetchone()['count']
    
    # Get date range
    cursor.execute("SELECT MIN(timestamp) as first, MAX(timestamp) as last FROM messages")
    date_range = cursor.fetchone()
    
    conn.close()
    
    stats = {
        'total_messages': total_count,
        'first_message': date_range['first'] if date_range['first'] else None,
        'last_message': date_range['last'] if date_range['last'] else None
    }
    
    return jsonify(stats)

def extract_and_save_entities(message_id, transcript):
    """
    Extract entities from a message transcript and save them to the database.
    
    Args:
        message_id: The ID of the message
        transcript: The text content of the message
    
    Returns:
        A tuple of (entities, error_message)
        - entities: A list of extracted entities, or empty list if extraction failed
        - error_message: None if successful, or an error message if extraction failed
    """
    try:
        # Get LLM client
        llm_client = get_llm_client()
        
        # Check if LLM is connected
        if not llm_client.is_connected and not llm_client.check_connectivity():
            error_msg = f"LLM service ({llm_client.provider}) is not reachable. Please check your configuration and ensure the service is running."
            print(error_msg)
            return [], error_msg
        
        # Extract entities
        entities = llm_client.extract_entities(transcript)
        
        if not entities:
            print(f"No entities extracted for message {message_id}")
            return [], None  # No error, just no entities found
        
        # Save entities to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, clear existing entity associations for this message
        cursor.execute("DELETE FROM note_entities WHERE message_id = ?", (message_id,))
        
        for entity in entities:
            # Check if this entity already exists (by type and label)
            cursor.execute(
                "SELECT id, color FROM entities WHERE type = ? AND label = ?",
                (entity['type'], entity['label'])
            )
            existing = cursor.fetchone()
            
            if existing:
                # Use existing entity
                entity_id = existing['id']
                # Keep the existing color
                entity['color'] = existing['color']
            else:
                # Insert new entity
                cursor.execute(
                    "INSERT INTO entities (type, label, color) VALUES (?, ?, ?)",
                    (entity['type'], entity['label'], entity['color'])
                )
                entity_id = cursor.lastrowid
            
            # Create association between message and entity
            cursor.execute(
                "INSERT INTO note_entities (message_id, entity_id) VALUES (?, ?)",
                (message_id, entity_id)
            )
        
        conn.commit()
        conn.close()
        
        return entities, None  # Success, no error
    except Exception as e:
        error_msg = f"Error extracting entities: {e}"
        print(error_msg)
        return [], error_msg

@app.route('/api/messages', methods=['POST'])
def create_message():
    """API endpoint to create a new message."""
    data = request.json
    
    if not data or 'timestamp' not in data or 'transcript' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO messages (timestamp, transcript) VALUES (?, ?)",
        (data['timestamp'], data['transcript'])
    )
    
    # Get the ID of the newly inserted message
    message_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    # Extract and save entities
    entities, error_msg = extract_and_save_entities(message_id, data['transcript'])
    
    response = {
        'id': message_id, 
        'success': True,
        'entities': entities
    }
    
    if error_msg:
        response['warning'] = error_msg
    
    return jsonify(response), 201

@app.route('/api/messages/<int:message_id>', methods=['PUT'])
def update_message(message_id):
    """API endpoint to update an existing message."""
    data = request.json
    
    if not data or ('timestamp' not in data and 'transcript' not in data):
        return jsonify({'error': 'Missing fields to update'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the message exists
    cursor.execute("SELECT id, transcript FROM messages WHERE id = ?", (message_id,))
    message = cursor.fetchone()
    if not message:
        conn.close()
        return jsonify({'error': 'Message not found'}), 404
    
    # Update the message
    update_fields = []
    params = []
    
    if 'timestamp' in data:
        update_fields.append("timestamp = ?")
        params.append(data['timestamp'])
    
    transcript_updated = False
    if 'transcript' in data:
        update_fields.append("transcript = ?")
        params.append(data['transcript'])
        transcript_updated = True
    
    params.append(message_id)
    
    cursor.execute(
        f"UPDATE messages SET {', '.join(update_fields)} WHERE id = ?",
        params
    )
    
    conn.commit()
    conn.close()
    
    # If transcript was updated, re-extract entities
    entities = []
    error_msg = None
    if transcript_updated:
        entities, error_msg = extract_and_save_entities(message_id, data['transcript'])
    
    response = {
        'success': True,
        'entities': entities
    }
    
    if error_msg:
        response['warning'] = error_msg
    
    return jsonify(response)

@app.route('/api/messages/<int:message_id>/entities')
def get_message_entities(message_id):
    """API endpoint to get entities for a specific message."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the message exists
    cursor.execute("SELECT id FROM messages WHERE id = ?", (message_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Message not found'}), 404
    
    # Get entities for this message
    cursor.execute("""
        SELECT e.id, e.type, e.label, e.color
        FROM entities e
        JOIN note_entities ne ON e.id = ne.entity_id
        WHERE ne.message_id = ?
        ORDER BY e.type, e.label
    """, (message_id,))
    
    entities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(entities)

@app.route('/api/entities')
def get_all_entities():
    """API endpoint to get all entities."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, type, label, color
        FROM entities
        ORDER BY type, label
    """)
    
    entities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(entities)

@app.route('/api/entities/<int:entity_id>', methods=['PUT'])
def update_entity(entity_id):
    """API endpoint to update an entity."""
    data = request.json
    
    if not data or not any(key in data for key in ['type', 'label', 'color']):
        return jsonify({'error': 'Missing fields to update'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the entity exists
    cursor.execute("SELECT id FROM entities WHERE id = ?", (entity_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Entity not found'}), 404
    
    # Update the entity
    update_fields = []
    params = []
    
    if 'type' in data:
        update_fields.append("type = ?")
        params.append(data['type'])
    
    if 'label' in data:
        update_fields.append("label = ?")
        params.append(data['label'])
    
    if 'color' in data:
        update_fields.append("color = ?")
        params.append(data['color'])
    
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    params.append(entity_id)
    
    cursor.execute(
        f"UPDATE entities SET {', '.join(update_fields)} WHERE id = ?",
        params
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/entities/merge', methods=['POST'])
def merge_entities():
    """API endpoint to merge multiple entities into one."""
    data = request.json
    
    if not data or 'entity_ids' not in data or 'merged_entity' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    entity_ids = data['entity_ids']
    merged_entity = data['merged_entity']
    
    if not entity_ids or len(entity_ids) < 2:
        return jsonify({'error': 'At least two entities must be specified for merging'}), 400
    
    if not all(key in merged_entity for key in ['type', 'label', 'color']):
        return jsonify({'error': 'Merged entity must have type, label, and color'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Create the merged entity
        cursor.execute(
            "INSERT INTO entities (type, label, color) VALUES (?, ?, ?)",
            (merged_entity['type'], merged_entity['label'], merged_entity['color'])
        )
        
        merged_id = cursor.lastrowid
        
        # Update all note_entities references to point to the merged entity
        placeholders = ','.join(['?'] * len(entity_ids))
        cursor.execute(f"""
            UPDATE note_entities
            SET entity_id = ?
            WHERE entity_id IN ({placeholders})
        """, [merged_id] + entity_ids)
        
        # Delete the old entities
        cursor.execute(f"DELETE FROM entities WHERE id IN ({placeholders})", entity_ids)
        
        # Commit the transaction
        conn.commit()
        
        return jsonify({
            'success': True,
            'merged_id': merged_id
        })
    
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        print(f"Error merging entities: {e}")
        return jsonify({'error': f'Error merging entities: {str(e)}'}), 500
    
    finally:
        conn.close()

@app.route('/api/config/llm', methods=['GET'])
def get_llm_config_endpoint():
    """API endpoint to get the current LLM configuration."""
    llm_config = config.get_llm_config()
    return jsonify(llm_config)

@app.route('/api/config/llm', methods=['PUT'])
def update_llm_config_endpoint():
    """API endpoint to update the LLM configuration."""
    data = request.json
    
    if not data:
        return jsonify({'error': 'Missing configuration data'}), 400
    
    provider = data.get('provider')
    if provider and provider not in ['ollama', 'openai', 'anthropic']:
        return jsonify({'error': f'Unsupported provider: {provider}'}), 400
    
    # Update configuration
    try:
        if provider:
            config.update_llm_config(provider=provider)
        
        # Update provider-specific configuration
        current_provider = config.get_llm_config()['provider']
        provider_config = data.get(current_provider, {})
        
        if provider_config:
            config.update_llm_config(**provider_config)
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"Error updating LLM configuration: {e}")
        return jsonify({'error': f'Error updating configuration: {str(e)}'}), 500

@app.route('/api/messages/<int:message_id>/extract-entities', methods=['POST'])
def extract_entities_endpoint(message_id):
    """API endpoint to manually trigger entity extraction for a message."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the message exists and get its transcript
    cursor.execute("SELECT transcript FROM messages WHERE id = ?", (message_id,))
    message = cursor.fetchone()
    
    if not message:
        conn.close()
        return jsonify({'error': 'Message not found'}), 404
    
    conn.close()
    
    # Extract and save entities
    entities, error_msg = extract_and_save_entities(message_id, message['transcript'])
    
    if error_msg:
        return jsonify({
            'success': False,
            'error': error_msg,
            'entities': []
        }), 500
    
    return jsonify({
        'success': True,
        'entities': entities
    })

@app.route('/api/test/extract', methods=['POST'])
def test_extract_entities():
    """API endpoint to test entity extraction with custom parameters."""
    data = request.json
    
    if not data or 'note' not in data or 'provider' not in data or 'prompt' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    note = data['note']
    provider = data['provider']
    custom_prompt = data['prompt']
    
    if not note.strip():
        return jsonify({'error': 'Note cannot be empty'}), 400
    
    if not custom_prompt.strip():
        return jsonify({'error': 'Prompt cannot be empty'}), 400
    
    # Get provider-specific config
    llm_config = config.get_llm_config()
    provider_config = llm_config.get(provider, {})
    
    try:
        # Create LLM client with the specified provider
        llm_client = LLMClient(provider=provider, config=provider_config)
        
        # Check if LLM is connected
        if not llm_client.is_connected and not llm_client.check_connectivity():
            error_msg = f"LLM service ({provider}) is not reachable. Please check your configuration and ensure the service is running."
            return jsonify({
                'error': error_msg,
                'entities': []
            }), 500
        
        # Store the original method to restore it later
        original_method = llm_client._create_extraction_prompt
        
        # Override the prompt method to use our custom prompt
        def custom_prompt_method(text):
            # If the custom prompt contains {text}, replace it with the actual text
            # Otherwise, append the text at the end (after "Text to analyze:")
            if "{text}" in custom_prompt:
                return custom_prompt.replace("{text}", text)
            else:
                # Find the "Text to analyze:" line and append the text after it
                lines = custom_prompt.split('\n')
                for i, line in enumerate(lines):
                    if "Text to analyze:" in line:
                        # If there's content after "Text to analyze:", replace it
                        if line.strip() != "Text to analyze:":
                            lines[i] = "Text to analyze:"
                        # Add the text on the next line
                        lines.insert(i + 1, text)
                        break
                else:
                    # If "Text to analyze:" not found, just append the text at the end
                    lines.append("Text to analyze:")
                    lines.append(text)
                
                return '\n'.join(lines)
        
        # Monkey patch the method
        llm_client._create_extraction_prompt = custom_prompt_method
        
        # Get the raw response before parsing
        raw_response = ""
        
        # Override the _parse_llm_response method to capture the raw response
        original_parse_method = llm_client._parse_llm_response
        def capture_response_method(response_text):
            nonlocal raw_response
            raw_response = response_text
            return original_parse_method(response_text)
        
        llm_client._parse_llm_response = capture_response_method
        
        # Extract entities
        entities = llm_client.extract_entities(note)
        
        # Restore original methods
        llm_client._create_extraction_prompt = original_method
        llm_client._parse_llm_response = original_parse_method
        
        return jsonify({
            'success': True,
            'entities': entities,
            'raw_response': raw_response
        })
        
    except Exception as e:
        error_msg = f"Error extracting entities: {str(e)}"
        print(error_msg)
        return jsonify({
            'error': error_msg,
            'entities': []
        }), 500

if __name__ == '__main__':
    # Ensure the database exists
    if not Path('transcripts.db').exists():
        conn = sqlite3.connect('transcripts.db')
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            transcript TEXT NOT NULL
        )
        ''')
        
        # Create entities table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            label TEXT NOT NULL,
            color TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create note_entities junction table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS note_entities (
            message_id INTEGER NOT NULL,
            entity_id INTEGER NOT NULL,
            PRIMARY KEY (message_id, entity_id),
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
        print("Created empty database file with schema")
    else:
        # Ensure the new tables exist even if the database file already exists
        conn = sqlite3.connect('transcripts.db')
        cursor = conn.cursor()
        
        # Check if entities table exists, create if not
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                label TEXT NOT NULL,
                color TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            print("Created entities table")
        
        # Check if note_entities table exists, create if not
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='note_entities'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS note_entities (
                message_id INTEGER NOT NULL,
                entity_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, entity_id),
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
            ''')
            print("Created note_entities table")
            
        conn.commit()
        conn.close()
    
    # Create static and templates directories if they don't exist
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True)
