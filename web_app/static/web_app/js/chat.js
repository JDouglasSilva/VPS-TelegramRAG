let currentSessionId = null;

// Carregar histórico inicial
async function loadHistory() {
    const res = await fetch('/api/chats/');
    const chats = await res.json();
    const historyDiv = document.getElementById('chatHistory');
    historyDiv.innerHTML = '';

    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = `chat-item ${currentSessionId === chat.id ? 'active' : ''}`;
        item.innerText = chat.title;
        item.onclick = () => selectSession(chat.id);
        historyDiv.appendChild(item);
    });
}

async function selectSession(id) {
    currentSessionId = id;
    const res = await fetch(`/api/chats/${id}/`);
    const chat = await res.json();

    document.getElementById('chatTitle').innerText = chat.title;
    const container = document.getElementById('chatContainer');
    container.innerHTML = '';

    chat.messages.forEach(msg => {
        addMessage(msg.content, msg.sender.toLowerCase(), msg.context_sources);
    });

    loadHistory();
}

function addMessage(text, sender, sources = []) {
    const container = document.getElementById('chatContainer');
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerText = text;

    if (sender === 'bot' && sources.length > 0) {
        const btn = document.createElement('button');
        btn.className = 'sources-btn';
        btn.innerText = 'Ver fontes';
        btn.onclick = () => showSources(sources);
        div.appendChild(btn);
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('userInput');
    const query = input.value.trim();
    if (!query) return;

    if (!currentSessionId) {
        // Criar nova sessão se não houver
        const res = await fetch('/api/chats/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ title: query.substring(0, 30) })
        });
        const session = await res.json();
        currentSessionId = session.id;
    }

    addMessage(query, 'user');
    input.value = '';

    const res = await fetch(`/api/chats/${currentSessionId}/ask/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ query })
    });
    const botMsg = await res.json();
    addMessage(botMsg.content, 'bot', botMsg.context_sources);
}

function showSources(sourceIds) {
    document.getElementById('sourcesModal').style.display = 'flex';
    const list = document.getElementById('sourcesList');
    list.innerHTML = `<p style="color:var(--text-muted)">Contexto recuperado de ${sourceIds.length} blocos de documentos da organização.</p>`;
}

function showUpload() {
    document.getElementById('uploadModal').style.display = 'flex';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const status = document.getElementById('uploadStatus');
    if (fileInput.files.length === 0) return;

    status.innerText = 'Subindo...';
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const res = await fetch('/api/documents/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData
    });

    if (res.ok) {
        status.innerText = 'Sucesso! O processamento começou em background.';
        setTimeout(() => closeModal('uploadModal'), 2000);
    } else {
        status.innerText = 'Erro no upload.';
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.getElementById('sendBtn').onclick = sendMessage;
document.getElementById('userInput').onkeypress = (e) => e.key === 'Enter' && sendMessage();
document.getElementById('uploadBtn').onclick = uploadFile;
document.getElementById('newChat').onclick = () => {
    currentSessionId = null;
    document.getElementById('chatContainer').innerHTML = '';
    document.getElementById('chatTitle').innerText = 'Novo Chat';
    loadHistory();
};

loadHistory();
