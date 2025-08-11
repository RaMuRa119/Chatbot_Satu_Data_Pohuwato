# backend.py  (atau ganti file lama)
import google.generativeai as genai
from flask_cors import CORS
import os
import json
from flask import Flask, request, jsonify
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import threading
import copy

app = Flask(__name__)
CORS(app, origins=['*'])

# --------------------------
# CONFIG
# --------------------------
# Gunakan env var untuk API key (lebih aman)
GENAI_API_KEY = os.environ.get("GENAI_API_KEY", "YOUR_API_KEY")
# Max jumlah pesan (user/model) yang disimpan di memory (last N messages)
MAX_MEMORY_MESSAGES = 30

# Lokasi file FAISS index dan data JSON
index_file_path = "index_faiss.bin"  # Sesuaikan path index Anda
data_file_path = "output.json"

# --------------------------
# TEMP IN-MEMORY MEMORY
# --------------------------
# Struktur: list of dicts: {"role": "user" / "model", "text": "..."}
TEMP_MEMORY = []
TEMP_MEMORY_LOCK = threading.Lock()

def push_memory(role, text):
    """Tambahkan entry ke TEMP_MEMORY (thread-safe) dan batasi panjang."""
    if text is None:
        return
    entry = {"role": role, "text": str(text)}
    with TEMP_MEMORY_LOCK:
        TEMP_MEMORY.append(entry)
        # keep only last MAX_MEMORY_MESSAGES entries
        if len(TEMP_MEMORY) > MAX_MEMORY_MESSAGES:
            # remove older ones
            del TEMP_MEMORY[0 : len(TEMP_MEMORY) - MAX_MEMORY_MESSAGES]

def get_memory_copy():
    """Ambil salinan memory saat ini (thread-safe)."""
    with TEMP_MEMORY_LOCK:
        return copy.deepcopy(TEMP_MEMORY)

def clear_memory():
    """Optional: fungsi untuk mengosongkan memory manual (kapanpun)."""
    with TEMP_MEMORY_LOCK:
        TEMP_MEMORY.clear()

# --------------------------
# JSON read helper
# --------------------------
def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            print(f"SUCCESS: File '{file_path}' successfully read.")
            return data
    except FileNotFoundError:
        print(f"ERROR: File '{file_path}' not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode JSON file '{file_path}' - {e}")
        return {}
    except Exception as e:
        print(f"ERROR: An unexpected error occurred - {e}")
        return {}

data = read_json_file(data_file_path)

# --------------------------
# GeminiChatBot wrapper
# --------------------------
class GeminiChatBot:
    def __init__(self, initial_history=None):
        genai.configure(api_key=GENAI_API_KEY)

        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "max_output_tokens": 4096,
            }
        )

        # chat_history will be list of content objects compatible with your usage
        # keep in same shape used previously: {"role": "user", "parts":[{"text": "..."}]}
        self.chat_history = []

        if initial_history:
            # initial_history expected as list of {"role": "user"/"model", "text": "..."}
            for msg in initial_history:
                role = msg.get("role", "user")
                text = msg.get("text", "")
                content = {"role": role, "parts": [{"text": text}]}
                self.chat_history.append(content)

    def send_message(self, message):
        # add incoming user message to chat_history
        if message:
            user_content = {"role": "user", "parts": [{"text": message}]}
            self.chat_history.append(user_content)

        try:
            chat_session = self.model.start_chat(history=self.chat_history.copy())
            # we send the last user message as content
            response = chat_session.send_message({"role": "user", "parts": [{"text": message}]})
            # append model response to history
            self.chat_history.append({"role": "model", "parts": [{"text": response.text}]})
            return response.text
        except KeyError as e:
            print(f"Error: {str(e)}")
            return "An error occurred while processing your message"
        except Exception as e:
            print(f"Unexpected error in send_message: {e}")
            return "An unexpected error occurred while processing your message"

    # optional: file-based history not used by temp-memory approach, keep for compatibility
    def save_history(self):
        try:
            with open('chat_history.json', 'w') as f:
                json.dump(self.chat_history, f, indent=4)
            print("Chat history saved successfully.")
        except Exception as e:
            print(f"Failed to save chat history: {str(e)}")

    def load_history(self):
        try:
            with open('chat_history.json', 'r') as f:
                self.chat_history = json.load(f)
        except FileNotFoundError:
            print("No chat history found. Starting a new session.")

# --------------------------
# FAISS search helpers (unchanged)
# --------------------------
def search(search_text, distance_threshold):
    # Muat kembali index dari file
    loaded_index = faiss.read_index(index_file_path)
    print("Index loaded successfully")

    encoder = SentenceTransformer("all-MiniLM-L6-v2")

    search_vector = encoder.encode(search_text)
    _vector = np.array([search_vector])
    faiss.normalize_L2(_vector)

    k = loaded_index.ntotal
    distances, ann = loaded_index.search(_vector, k=k)

    keys = list(data.keys())  # Mengambil semua key dari dictionary
    search_result = []

    for i in range(len(ann[0])):
        idx = ann[0][i]
        dist = distances[0][i]
        if idx < len(keys) and dist <= distance_threshold:  # Validasi index dan threshold
            key = keys[idx]
            search_result.append({
                'title': key,
                'category': data[key]['category'],
                'data': data[key]['data']
            })

    return search_result

def format_retrieved_data_dynamic(data_item):
    table = "Data yang Diretrieve:\n\n"
    title = data_item['title']
    category = data_item['category']
    table += f"{title} ({category}):\n"

    if data_item['data']:
        headers = data_item['data'][0].keys()
        header_line = ' '.join([f"{header:<20}" for header in headers])
        table += header_line + "\n"
        table += "-" * len(header_line) + "\n"

        for row in data_item['data']:
            row_line = ' '.join([f"{str(row.get(header, '')):<20}" for header in headers])
            table += row_line + "\n"
    return table

# --------------------------
# Flask route
# --------------------------
@app.route('/chat_submit', methods=['POST'])
def chat_endpoint():
    # Ambil current temp-memory (last messages)
    current_memory = get_memory_copy()

    data_in = request.get_json()
    inputChat = data_in.get('prompt', '')
    distance_threshold = data_in.get('threshold', 0.8)

    # Cek dengan FAISS terlebih dahulu
    search_results = search(inputChat, distance_threshold)

    # Jika FAISS menemukan, format & kirim ke model
    if search_results:
        formatted_result = format_retrieved_data_dynamic(search_results[0])

        # Create chatbot with initial_history populated from TEMP_MEMORY
        chatbot = GeminiChatBot(initial_history=current_memory)
        # Send the retrieved formatted table and the user prompt (so model sees both memory + retrieved table)
        combined_prompt = f"{inputChat}\n\nBerikut adalah data yang diretrieve:\n{formatted_result}"
        response_text = chatbot.send_message(combined_prompt)

        # Update TEMP_MEMORY with the user input that triggered this and model response
        # We store both the original user prompt and the model reply (and optionally the formatted RAG content)
        push_memory("user", inputChat)
        # optionally also push the formatted RAG content (makes model remember what was retrieved)
        push_memory("user", formatted_result)  # role 'user' optional; adjust as you like
        push_memory("model", response_text)

        return jsonify({
            "status": "success",
            "source": "retrieval_augmented",
            "search_result": search_results[0],
            "formatted": formatted_result,
            "response": response_text
        })

    # Jika tidak ada hasil FAISS -> langsung ke model (tetap diberikan memory)
    chatbot = GeminiChatBot(initial_history=current_memory)
    response_text = chatbot.send_message(inputChat)

    # simpan ke TEMP_MEMORY
    push_memory("user", inputChat)
    push_memory("model", response_text)

    return jsonify({
        "status": "success",
        "source": "gemini_only",
        "response": response_text
    })

if __name__ == '__main__':
    app.run(debug=True)
