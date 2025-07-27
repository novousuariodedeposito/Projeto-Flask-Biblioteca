import json
from flask import Flask, render_template, request, render_template_string, redirect, url_for, jsonify
import os
import platform
from datetime import datetime
from keep_alive import keep_alive

app = Flask(__name__)


keep_alive()

# Armazena listas de filmes e séries por usuário
user_data = {}
ngrok_link = ""  # Variável para armazenar o link do ngrok

if os.path.exists("media_lists.json"):
    try:
        with open("media_lists.json", "r", encoding="utf-8") as file:
            user_data = json.load(file)
    except json.JSONDecodeError:
        user_data = {}  # Cria um dicionário vazio se o JSON for inválido
else:
    user_data = {}  # Cria um dicionário vazio se o arquivo não existir


def save_data():
    with open("media_lists.json", "w", encoding="utf-8") as file:
        json.dump(user_data, file, indent=4)

def get_client_ip():
    """Obtém o IP real do cliente"""
    # Verifica headers de proxy primeiro
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_device_info():
    """Coleta informações detalhadas do dispositivo/navegador"""
    user_agent = request.headers.get('User-Agent', '')
    
    # Detecta tipo de dispositivo
    is_mobile = any(keyword in user_agent.lower() for keyword in 
                   ['mobile', 'android', 'iphone', 'ipad', 'windows phone'])
    
    # Detecta navegador
    browser = 'Unknown'
    if 'Chrome' in user_agent:
        browser = 'Chrome'
    elif 'Firefox' in user_agent:
        browser = 'Firefox'
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        browser = 'Safari'
    elif 'Edge' in user_agent:
        browser = 'Edge'
    
    # Detecta sistema operacional
    os_info = 'Unknown'
    if 'Windows' in user_agent:
        os_info = 'Windows'
    elif 'Mac' in user_agent:
        os_info = 'macOS'
    elif 'Linux' in user_agent:
        os_info = 'Linux'
    elif 'Android' in user_agent:
        os_info = 'Android'
    elif 'iOS' in user_agent or 'iPhone' in user_agent or 'iPad' in user_agent:
        os_info = 'iOS'
    
    return {
        'user_agent': user_agent,
        'is_mobile': is_mobile,
        'browser': browser,
        'os': os_info,
        'language': request.headers.get('Accept-Language', '').split(',')[0] if request.headers.get('Accept-Language') else 'Unknown'
    }

def log_access(ip, page, username=None, action=None, extra_data=None):
    """Registra acesso com informações detalhadas"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    device_info = get_device_info()
    
    # Carrega logs existentes
    if os.path.exists("access_logs.json"):
        try:
            with open("access_logs.json", "r", encoding="utf-8") as file:
                logs = json.load(file)
        except json.JSONDecodeError:
            logs = []
    else:
        logs = []
    
    # Adiciona novo log com informações detalhadas
    log_entry = {
        "timestamp": timestamp,
        "ip": ip,
        "page": page,
        "username": username,
        "action": action,  # Ex: 'login', 'add_movie', 'delete_item', etc.
        "device_info": device_info,
        "referer": request.headers.get('Referer', ''),
        "method": request.method,
        "extra_data": extra_data or {}
    }
    
    logs.append(log_entry)
    
    # Mantém apenas os últimos 2000 logs
    if len(logs) > 2000:
        logs = logs[-2000:]
    
    # Salva logs
    with open("access_logs.json", "w", encoding="utf-8") as file:
        json.dump(logs, file, indent=4)

def save_data():
    with open("media_lists.json", "w", encoding="utf-8") as file:
        json.dump(user_data, file, indent=4)


def limpar_input(texto):
    """Limpa e normaliza texto para comparações"""
    if not texto or not isinstance(texto, str):
        return ""
    return texto.strip().lower()

def validar_titulo(titulo):
    """Valida se o título é válido"""
    if not titulo or not isinstance(titulo, str):
        return False
    titulo_limpo = titulo.strip()
    if len(titulo_limpo) < 1 or len(titulo_limpo) > 200:
        return False
    return True

def validar_categoria(categoria):
    """Valida se a categoria é válida"""
    return categoria in ["filme", "serie"]

def inicializar_usuario(username):
    """Inicializa estrutura de dados do usuário"""
    if username not in user_data:
        user_data[username] = {
            "movies": [],
            "series": [],
            "abertos": {
                "movies": [],
                "series": []
            }
        }


@app.route('/')
def index():
    client_ip = get_client_ip()
    log_access(client_ip, "index")
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    client_ip = get_client_ip()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        log_access(client_ip, "login_attempt", username, "attempt", 
                   {"form_username": username})
        
        # Validações
        if not username:
            log_access(client_ip, "login_fail", username, "validation_error", 
                      {"error": "empty_username"})
            return render_template('login.html', error="Usuário não pode ser vazio!")
        
        if len(username) < 2 or len(username) > 50:
            log_access(client_ip, "login_fail", username, "validation_error", 
                      {"error": "invalid_length", "length": len(username)})
            return render_template('login.html', error="Nome deve ter entre 2 e 50 caracteres!")
        
        # Caracteres permitidos
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            log_access(client_ip, "login_fail", username, "validation_error", 
                      {"error": "invalid_characters"})
            return render_template('login.html', error="Use apenas letras, números, _ ou -")
        
        # Inicializa usuário se não existir
        was_new_user = username not in user_data
        inicializar_usuario(username)
        save_data()
        
        log_access(client_ip, "login_success", username, "success", 
                   {"new_user": was_new_user, "total_movies": len(user_data[username]["movies"]), 
                    "total_series": len(user_data[username]["series"])})
        return redirect(url_for('my_biblioteca', username=username))
    
    log_access(client_ip, "login_page", None, "page_view")
    return render_template('login.html')


@app.route('/mybiblioteca', methods=['GET'])
def my_biblioteca():
    username = request.args.get('username')
    client_ip = get_client_ip()
    log_access(client_ip, "mybiblioteca", username)
    
    if username not in user_data:
        return "Usuário não encontrado!", 404

    return render_template_string('''
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link rel="stylesheet" href="/static/styles.css">
<title>Minha Biblioteca - {{ username }}</title>
<body class="biblioteca-page">
    <div class="biblioteca-container">
        <div class="header">
            <h1>🎬 Biblioteca de {{ username }}</h1>
            <a href="/login" class="logout-button">Sair</a>
        </div>

        <form id="addForm" class="add-form">
            <input type="hidden" name="username" value="{{ username }}">
            <input type="text" name="title" placeholder="Título do filme ou série" required>
            <select name="category" required>
                <option value="filme">Filme</option>
                <option value="serie">Série</option>
            </select>
            <button type="submit" class="add-button">Adicionar</button>
        </form>

        <div class="section">
            <h2 class="toggle" data-target="movies">🎞️ Seus Filmes</h2>
            <div id="movies" class="content-grid" style="display: none;">
                {% for movie in movies %}
                    <div class="card">
                        <span>{{ movie }}</span>
                        <button class="delete delete-button" data-title="{{ movie }}" data-category="filme">Deletar</button>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2 class="toggle" data-target="series">📺 Suas Séries</h2>
            <div id="series" class="content-grid" style="display: none;">
                {% for serie in series %}
                    <div class="card">
                        <span>{{ serie }}</span>
                        <button class="delete delete-button" data-title="{{ serie }}" data-category="serie">Deletar</button>
                    </div>
                {% endfor %}
            </div>
        </div>
                                  
        <div class="section">
        <h2 class="toggle" onclick="goToAberto('{{ username }}')">🎯 Em Aberto</h2>
        </div>
                                  
        <script>
        // redireciona para a página "Em Aberto"
        function goToAberto(username) {
            const form = document.createElement('form');
            form.method = 'GET';
            form.action = '/em_aberto';

            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'username';
            input.value = username;

            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
        }
        </script>
                  
        <div class="view-other">
            <h3 class="view-title">🔍 Ver lista de outro usuário</h3>
            <form method="post" action="/view_other" class="view-form">
                <input type="hidden" name="username" value="{{ username }}">
                <select name="other_username" class="view-select">
                    {% for user in users if user != username %}
                        <option value="{{ user }}">{{ user }}</option>
                    {% endfor %}
                </select>
                <button type="submit" name="action" value="view" class="view-button">Ver Lista</button>
            </form>
        </div>
    </div>
       <h3 class="view-title">🔍 Ver lista de Em Abertos</h3>
         <form method="post" action="/view_aberto" class="view-form">
            <input type="hidden" name="username" value="{{ username }}">
            <select name="other_username" class="view-select">
            {% for user in users if user != username %}
                <option value="{{ user }}">{{ user }}</option>
            {% endfor %}
        </select>
        <button type="submit" name="action" value="view_aberto" class="view-button">Ver Em Aberto</button>
    </form>


    <div id="toast" class="toast"></div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        function showToast(message, isError = false) {
            const toast = document.getElementById("toast");
            toast.textContent = message;
            toast.className = "toast" + (isError ? " error" : "");
            toast.classList.add("show");
            setTimeout(() => {
                toast.classList.remove("show");
            }, 3000);
        }

        function toggleSection(sectionId) {
            const section = document.getElementById(sectionId);
            if (section.style.display === "none" || section.style.display === "") {
                section.style.display = "grid";
            } else {
                section.style.display = "none";
            }
        }

        document.querySelectorAll('.toggle').forEach(function (toggle) {
            toggle.addEventListener('click', function () {
                toggleSection(this.getAttribute('data-target'));
            });
        });

        function attachDeleteEvent(button) {
            button.addEventListener('click', function () {
                const title = this.getAttribute('data-title');
                const category = this.getAttribute('data-category');

                fetch('/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: '{{ username }}',
                        title: title,
                        category: category
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.closest('.card').remove();
                        showToast(`${title} foi deletado da sua lista de ${category === 'filme' ? 'filmes' : 'séries'}`);
                    } else {
                        showToast('Erro ao deletar item.', true);
                    }
                });
            });
        }

        document.querySelectorAll('.delete-button').forEach(btn => attachDeleteEvent(btn));

        document.getElementById('addForm').addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(this);
            const title = formData.get("title");
            const category = formData.get("category");

            fetch('/add', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const containerId = category === 'filme' ? 'movies' : 'series';
                    const container = document.getElementById(containerId);

                    const card = document.createElement('div');
                    card.className = 'card';

                    const span = document.createElement('span');
                    span.textContent = title;
                    card.appendChild(span);

                    const delBtn = document.createElement('button');
                    delBtn.textContent = 'Deletar';
                    delBtn.className = 'delete delete-button';
                    delBtn.setAttribute('data-title', title);
                    delBtn.setAttribute('data-category', category);
                    card.appendChild(delBtn);

                    container.appendChild(card);
                    attachDeleteEvent(delBtn);

                    showToast(`${title} foi adicionado como ${category === 'filme' ? 'filme' : 'série'}`);
                    this.reset();
                } else {
                    showToast('Erro ao adicionar item.', true);
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Erro inesperado.', true);
            });
        });
    });
</script>
</body>
''',
                                  username=username,
                                  movies=user_data[username]["movies"],
                                  series=user_data[username]["series"],
                                  users=user_data.keys())


@app.route('/view_other', methods=['POST'])
def view_other():
    username = request.form.get('username')
    other_user = request.form.get('other_username')
    if other_user in user_data:

        return render_template_string('''
 <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link rel="stylesheet" href="/static/styles.css">
<title>Lista de {{ other_username }}</title>
<body class="biblioteca-page">
    <div class="biblioteca-container">
        <div class="header">
            <h1>📚 Biblioteca de {{ other_username }}</h1>
            <a href="/login" class="logout-button">Sair</a>
        </div>

        <div class="section">
            <h2 class="toggle" data-target="other_movies">🎞️ Filmes</h2>
            <div id="other_movies" class="content-grid" style="display: none;">
                {% for movie in movies %}
                    <div class="card">
                        <span>{{ movie }}</span>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2 class="toggle" data-target="other_series">📺 Séries</h2>
            <div id="other_series" class="content-grid" style="display: none;">
                {% for serie in series %}
                    <div class="card">
                        <span>{{ serie }}</span>
                    </div>
                {% endfor %}
            </div>
        </div>

        <form method="get" action="/mybiblioteca" class="back-form">
            <input type="hidden" name="username" value="{{ username }}">
            <button type="submit" class="back-button">⬅ Voltar para Minha Biblioteca</button>
        </form>
    </div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        function toggleSection(sectionId) {
            const section = document.getElementById(sectionId);
            if (section.style.display === "none" || section.style.display === "") {
                section.style.display = "grid";
            } else {
                section.style.display = "none";
            }
        }

        document.querySelectorAll('.toggle').forEach(function (toggle) {
            toggle.addEventListener('click', function () {
                toggleSection(this.getAttribute('data-target'));
            });
        });
    });
</script>
</body>
''',
                                      username=username,
                                      other_username=other_user,
                                      movies=user_data[other_user]["movies"],
                                      series=user_data[other_user]["series"])

    return "Usuário não encontrado!", 404


# Rota para deletar item
@app.route('/delete', methods=['POST'])
def delete_item():
    data = request.get_json()
    username = data.get('username')
    title = data.get('title')
    category = data.get('category')
    client_ip = get_client_ip()

    if username in user_data:
        # Conta itens antes da deleção
        old_count = len(user_data[username]["movies"] if category == "filme" else user_data[username]["series"])
        
        if category == "filme":
            user_data[username]["movies"] = [
                m for m in user_data[username]["movies"]
                if m.lower() != title.lower()
            ]
        elif category == "serie":
            user_data[username]["series"] = [
                s for s in user_data[username]["series"]
                if s.lower() != title.lower()
            ]
        
        new_count = len(user_data[username]["movies"] if category == "filme" else user_data[username]["series"])
        save_data()
        
        # Log da deleção
        log_access(client_ip, "delete_item_success", username, "delete_item", {
            "title": title,
            "category": category,
            "old_count": old_count,
            "new_count": new_count,
            "library_stats": {
                "total_movies": len(user_data[username]["movies"]),
                "total_series": len(user_data[username]["series"])
            }
        })
        
        return jsonify({"success": True})
    
    log_access(client_ip, "delete_item_fail", username, "user_not_found", 
              {"title": title, "category": category})
    return jsonify({"success": False}), 400


@app.route('/view_aberto', methods=['POST'])
def view_aberto():
    username = request.form.get('username')
    other_user = request.form.get('other_username')

    if other_user not in user_data:
        return "Usuário não encontrado!", 404

    data = user_data[other_user].get("abertos", {"movies": [], "series": []})

    return render_template_string('''
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/static/styles.css">
    <title>Em Aberto de {{ other_user }}</title>
    <body class="biblioteca-page">
    <div class="biblioteca-container">
        <div class="header">
            <h1>🎯 Lista Em Aberto de {{ other_user }}</h1>
            <a href="/login" class="logout-button">Sair</a>
        </div>

        <div class="section">
            <h2 class="toggle" data-target="other_abertos_filmes">🎞️ Filmes em Aberto</h2>
            <div id="other_abertos_filmes" class="content-grid" style="display: none;">
                {% for movie in movies %}
                    <div class="card"><span>{{ movie }}</span></div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2 class="toggle" data-target="other_abertos_series">📺 Séries em Aberto</h2>
            <div id="other_abertos_series" class="content-grid" style="display: none;">
                {% for serie in series %}
                    <div class="card"><span>{{ serie }}</span></div>
                {% endfor %}
            </div>
        </div>

        <form method="get" action="/mybiblioteca" class="back-form">
            <input type="hidden" name="username" value="{{ username }}">
            <button type="submit" class="back-button">⬅ Voltar</button>
        </form>
    </div>

    <script>
        document.querySelectorAll('.toggle').forEach(function(toggle) {
            toggle.addEventListener('click', function () {
                const section = document.getElementById(this.getAttribute('data-target'));
                section.style.display = (section.style.display === "none" || section.style.display === "") ? "grid" : "none";
            });
        });
    </script>
    </body>
    ''',
                                  username=username,
                                  other_user=other_user,
                                  movies=data.get("movies", []),
                                  series=data.get("series", []))


@app.route('/sync_em_aberto', methods=['GET'])
def sync_em_aberto():
    username = request.args.get('username')
    if not username or username not in user_data:
        return jsonify({"success": False, "error": "Usuário inválido"}), 400

    data = user_data[username].get("abertos", {"movies": [], "series": []})
    return jsonify({
        "success": True,
        "movies": data.get("movies", []),
        "series": data.get("series", [])
    })


@app.route('/em_aberto', methods=['GET', 'POST'])
def em_aberto():
    username = request.args.get('username')
    if not username or username not in user_data:
        return "Usuário inválido", 404

    # Inicializa campos se não existirem
    if "abertos" not in user_data[username]:
        user_data[username]["abertos"] = {"movies": [], "series": []}
        save_data()

    return render_template_string(
        '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Em Aberto</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="biblioteca-page">
    <div class="biblioteca-container">
        <div class="header">
            <h1>🎯 Lista Em Aberto de {{ username }}</h1>
            <a href="/login" class="logout-button">Sair</a>
        </div>
                                  
       <div id="toast" class="toast"></div>

        <!-- Formulário para adicionar -->
        <form id="addAbertoForm" class="add-form">
            <input type="hidden" name="username" value="{{ username }}">
            <input type="text" name="title" placeholder="Título do filme ou série" required>
            <select name="category">
                <option value="filme">Filme</option>
                <option value="serie">Série</option>
            </select>
            <button type="submit" class="add-button">Adicionar</button>
        </form>

        <!-- Filmes em aberto -->
        <div class="section">
            <h2 class="toggle" data-target="abertos_filmes">🎞️ Filmes em Aberto</h2>
            <div id="abertos_filmes" class="content-grid">
                {% for movie in movies %}
                    <div class="card">
                        <span>{{ movie }}</span>
                        <button class="delete-button delete-aberto-btn" data-title="{{ movie }}" data-category="filme" style="margin-top: 10px;">🗑 Deletar</button>
                        <button class="add-button mover-biblioteca-btn" data-title="{{ movie }}" data-category="filme">📥 Mover para Biblioteca</button>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- Séries em aberto -->
        <div class="section">
            <h2 class="toggle" data-target="abertos_series">📺 Séries em Aberto</h2>
            <div id="abertos_series" class="content-grid">
                {% for serie in series %}
                    <div class="card">
                        <span>{{ serie }}</span>
                        <button class="delete-button delete-aberto-btn" data-title="{{ serie }}" data-category="serie" style="margin-top: 10px;">🗑 Deletar</button>
                        <button class="add-button mover-biblioteca-btn" data-title="{{ serie }}" data-category="serie">📥 Mover para Biblioteca</button>
                    </div>
                {% endfor %}
            </div>
        </div>

        <form method="get" action="/mybiblioteca" class="back-form">
            <input type="hidden" name="username" value="{{ username }}">
            <button type="submit" class="back-button">⬅ Voltar</button>
        </form>
    </div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        function showToast(message, isError = false) {
            const toast = document.getElementById("toast");
            toast.textContent = message;
            toast.className = "toast" + (isError ? " error" : "");
            toast.classList.add("show");
            setTimeout(() => {
                toast.classList.remove("show");
            }, 3000);
        }

        document.querySelectorAll('.toggle').forEach(function (toggle) {
            toggle.addEventListener('click', function () {
                const target = document.getElementById(this.getAttribute('data-target'));
                target.style.display = (target.style.display === "none" || target.style.display === "") ? "grid" : "none";
            });
        });

        // Adicionar item via AJAX
        document.getElementById('addAbertoForm').addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(this);
            const title = formData.get("title");
            const category = formData.get("category");

            fetch('/add_aberto_ajax', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const containerId = category === 'filme' ? 'abertos_filmes' : 'abertos_series';
                    const container = document.getElementById(containerId);

                    const card = document.createElement('div');
                    card.className = 'card';

                    const span = document.createElement('span');
                    span.textContent = title;
                    card.appendChild(span);

                    const delBtn = document.createElement('button');
                    delBtn.textContent = '🗑 Deletar';
                    delBtn.className = 'delete-button delete-aberto-btn';
                    delBtn.setAttribute('data-title', title);
                    delBtn.setAttribute('data-category', category);
                    delBtn.style.marginTop = '10px';
                    card.appendChild(delBtn);

                    const moveBtn = document.createElement('button');
                    moveBtn.textContent = '📥 Mover para Biblioteca';
                    moveBtn.className = 'add-button mover-biblioteca-btn';
                    moveBtn.setAttribute('data-title', title);
                    moveBtn.setAttribute('data-category', category);
                    card.appendChild(moveBtn);

                    container.appendChild(card);
                    attachEvents(delBtn, moveBtn);

                    showToast(`${title} foi adicionado como ${category === 'filme' ? 'filme' : 'série'} em aberto`);
                    this.reset();
                } else {
                    showToast('Erro ao adicionar item.', true);
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Erro inesperado.', true);
            });
        });

        function attachEvents(delBtn, moveBtn) {
            delBtn.addEventListener('click', function () {
                const title = this.getAttribute('data-title');
                const category = this.getAttribute('data-category');

                fetch('/delete_aberto_ajax', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: '{{ username }}',
                        title: title,
                        category: category
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.closest('.card').remove();
                        showToast(`${title} foi removido dos em aberto`);
                    } else {
                        showToast('Erro ao deletar item.', true);
                    }
                });
            });

            moveBtn.addEventListener('click', function () {
                const title = this.getAttribute('data-title');
                const category = this.getAttribute('data-category');

                fetch('/mover_para_biblioteca_ajax', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: '{{ username }}',
                        title: title,
                        category: category
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.closest('.card').remove();
                        showToast(`${title} foi movido para a biblioteca`);
                    } else {
                        showToast('Erro ao mover item.', true);
                    }
                });
            });
        }

        // Anexar eventos aos botões existentes
        document.querySelectorAll('.delete-aberto-btn').forEach(btn => {
            const moveBtn = btn.nextElementSibling;
            attachEvents(btn, moveBtn);
        });

        // Inicia fechado no mobile
        if (window.innerWidth <= 600) {
            document.getElementById('abertos_filmes').style.display = "none";
            document.getElementById('abertos_series').style.display = "none";
        }
    });
</script>
</body>
</html>
''',
        username=username,
        movies=user_data[username]["abertos"]["movies"],
        series=user_data[username]["abertos"]["series"])


@app.route('/add_aberto', methods=['POST'])
def add_aberto():
    username = request.form.get('username')
    title = request.form.get('title')
    category = request.form.get('category')

    if username not in user_data or category not in ["filme", "serie"]:
        return "Dados inválidos", 400

    # Lista de usuários afetados: o próprio + parceiro
    affected_users = [username]
    key = "movies" if category == "filme" else "series"

    for user in affected_users:
        user_data.setdefault(user, {})
        user_data[user].setdefault("abertos", {"movies": [], "series": []})

        if title not in user_data[user]["abertos"][key]:
            user_data[user]["abertos"][key].append(title)

    save_data()
    return redirect(url_for('em_aberto', username=username))


@app.route('/add_aberto_ajax', methods=['POST'])
def add_aberto_ajax():
    try:
        username = request.form.get('username', '').strip()
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()

        # Validações
        if not username or username not in user_data:
            return jsonify({"success": False, "message": "Usuário inválido"}), 400
            
        if not validar_titulo(title):
            return jsonify({"success": False, "message": "Título inválido"}), 400
            
        if not validar_categoria(category):
            return jsonify({"success": False, "message": "Categoria inválida"}), 400

        # Inicializar estrutura se necessário
        inicializar_usuario(username)
        
        key = "movies" if category == "filme" else "series"
        title_normalizado = limpar_input(title)
        
        # Verificar duplicatas
        lista_atual = user_data[username]["abertos"][key]
        lista_normalizada = [limpar_input(t) for t in lista_atual if isinstance(t, str)]
        
        if title_normalizado in lista_normalizada:
            return jsonify({"success": False, "message": "Item já existe"}), 400

        # Adicionar
        user_data[username]["abertos"][key].append(title)
        save_data()
        
        return jsonify({
            "success": True, 
            "message": f"{title} adicionado aos em aberto!"
        })
        
    except Exception as e:
        print(f"Erro em add_aberto_ajax: {e}")
        return jsonify({
            "success": False,
            "message": "Erro interno do servidor"
        }), 500


@app.route('/delete_aberto', methods=['POST'])
def delete_aberto():
    username = request.form.get('username')
    title = request.form.get('title')
    category = request.form.get('category')

    if username not in user_data or category not in ["filme", "serie"]:
        return "Dados inválidos", 400

    # Define os usuários afetados
    affected_users = [username]
    key = "movies" if category == "filme" else "series"

    for user in affected_users:
        if user in user_data and "abertos" in user_data[user]:
            lista = user_data[user]["abertos"].get(key, [])
            user_data[user]["abertos"][key] = [
                t for t in lista if isinstance(t, str) and isinstance(title, str) and t.lower() != title.lower()
            ]

    save_data()
    return redirect(url_for('em_aberto', username=username))


@app.route('/mover_para_biblioteca', methods=['POST'])
def mover_para_biblioteca():
    username = request.form.get('username')
    title = request.form.get('title')
    category = request.form.get('category')

    if username not in user_data or category not in ["filme", "serie"]:
        return "Dados inválidos", 400

    affected_users = [username]
    key = "movies" if category == "filme" else "series"

    for user in affected_users:
        # Adiciona à biblioteca (se ainda não estiver)
        if title not in user_data[user][key]:
            user_data[user][key].append(title)

        # Remove da lista de abertos (se estiver)
        if title in user_data[user].get("abertos", {}).get(key, []):
            user_data[user]["abertos"][key].remove(title)

    save_data()
    return redirect(url_for('em_aberto', username=username))


@app.route('/delete_aberto_ajax', methods=['POST'])
def delete_aberto_ajax():
    data = request.get_json()
    username = data.get('username')
    title = data.get('title')
    category = data.get('category')

    if username not in user_data or category not in ["filme", "serie"]:
        return jsonify({"success": False}), 400

    key = "movies" if category == "filme" else "series"

    if username in user_data and "abertos" in user_data[username]:
        lista = user_data[username]["abertos"].get(key, [])
        user_data[username]["abertos"][key] = [
            t for t in lista if isinstance(t, str) and isinstance(title, str) and t.lower() != title.lower()
        ]

    save_data()
    return jsonify({"success": True})


@app.route('/mover_para_biblioteca_ajax', methods=['POST'])
def mover_para_biblioteca_ajax():
    data = request.get_json()
    username = data.get('username')
    title = data.get('title')
    category = data.get('category')

    if username not in user_data or category not in ["filme", "serie"]:
        return jsonify({"success": False}), 400

    key = "movies" if category == "filme" else "series"

    # Adiciona à biblioteca (se ainda não estiver)
    if title not in user_data[username][key]:
        user_data[username][key].append(title)

    # Remove da lista de abertos (se estiver)
    if title in user_data[username].get("abertos", {}).get(key, []):
        user_data[username]["abertos"][key].remove(title)

    save_data()
    return jsonify({"success": True})


@app.route('/admin/logs')
def view_logs():
    """Rota para visualizar logs de acesso (apenas para administração)"""
    client_ip = get_client_ip()
    log_access(client_ip, "admin_logs")
    
    if not os.path.exists("access_logs.json"):
        logs = []
    else:
        try:
            with open("access_logs.json", "r", encoding="utf-8") as file:
                logs = json.load(file)
        except json.JSONDecodeError:
            logs = []
    
    # Ordena por timestamp mais recente primeiro
    logs = sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Calcular estatísticas avançadas
    mobile_users = sum(1 for log in logs if log.get('device_info', {}).get('is_mobile', False))
    browsers = {}
    os_stats = {}
    actions_stats = {}
    
    for log in logs:
        device_info = log.get('device_info', {})
        browser = device_info.get('browser', 'Unknown')
        os_info = device_info.get('os', 'Unknown')
        action = log.get('action', 'Unknown')
        
        browsers[browser] = browsers.get(browser, 0) + 1
        os_stats[os_info] = os_stats.get(os_info, 0) + 1
        actions_stats[action] = actions_stats.get(action, 0) + 1

    return render_template_string('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Analytics Avançado</title>
    <link rel="stylesheet" href="/static/styles.css">
    <style>
        .logs-container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
            background: #1a1a1a;
            border-radius: 10px;
        }
        .log-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 12px;
        }
        .log-table th, .log-table td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #333;
            color: #fff;
        }
        .log-table th {
            background: #2d2d2d;
            font-weight: bold;
        }
        .log-table tr:hover {
            background: #2a2a2a;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #2d2d2d;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number {
            font-size: 1.8em;
            font-weight: bold;
            color: #4CAF50;
        }
        .back-button {
            background: #666;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-bottom: 20px;
        }
        .detailed-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-section {
            background: #2d2d2d;
            padding: 15px;
            border-radius: 8px;
        }
        .stat-section h3 {
            color: #4CAF50;
            margin-top: 0;
        }
        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #444;
            color: #ccc;
        }
        .mobile-badge {
            background: #ff9800;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
        }
        .desktop-badge {
            background: #2196F3;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
        }
    </style>
</head>
<body class="biblioteca-page">
    <div class="logs-container">
        <a href="/login" class="back-button">⬅ Voltar ao Login</a>
        
        <h1>📊 Analytics Avançado</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_logs }}</div>
                <div>Total de Acessos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ unique_ips }}</div>
                <div>IPs Únicos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ unique_users }}</div>
                <div>Usuários Únicos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ mobile_percentage }}%</div>
                <div>Usuários Mobile</div>
            </div>
        </div>
        
        <div class="detailed-stats">
            <div class="stat-section">
                <h3>🌐 Navegadores</h3>
                {% for browser, count in top_browsers %}
                <div class="stat-item">
                    <span>{{ browser }}</span>
                    <span>{{ count }}</span>
                </div>
                {% endfor %}
            </div>
            
            <div class="stat-section">
                <h3>💻 Sistemas Operacionais</h3>
                {% for os, count in top_os %}
                <div class="stat-item">
                    <span>{{ os }}</span>
                    <span>{{ count }}</span>
                </div>
                {% endfor %}
            </div>
            
            <div class="stat-section">
                <h3>🎯 Ações Mais Frequentes</h3>
                {% for action, count in top_actions %}
                <div class="stat-item">
                    <span>{{ action }}</span>
                    <span>{{ count }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <table class="log-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>IP</th>
                    <th>Usuário</th>
                    <th>Página</th>
                    <th>Ação</th>
                    <th>Dispositivo</th>
                    <th>Navegador</th>
                    <th>SO</th>
                    <th>Detalhes</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs[:50] %}
                <tr>
                    <td>{{ log.timestamp }}</td>
                    <td>{{ log.ip }}</td>
                    <td>{{ log.username or '-' }}</td>
                    <td>{{ log.page }}</td>
                    <td>{{ log.action or '-' }}</td>
                    <td>
                        {% if log.device_info and log.device_info.is_mobile %}
                            <span class="mobile-badge">📱 Mobile</span>
                        {% else %}
                            <span class="desktop-badge">🖥️ Desktop</span>
                        {% endif %}
                    </td>
                    <td>{{ log.device_info.browser if log.device_info else '-' }}</td>
                    <td>{{ log.device_info.os if log.device_info else '-' }}</td>
                    <td>
                        {% if log.extra_data %}
                            {{ log.extra_data|truncate(50) }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        {% if logs|length > 50 %}
        <p style="text-align: center; color: #888; margin-top: 20px;">
            Mostrando apenas os 50 logs mais recentes de {{ logs|length }} total
        </p>
        {% endif %}
    </div>
</body>
</html>
    ''', 
    logs=logs,
    total_logs=len(logs),
    unique_ips=len(set(log.get('ip', '') for log in logs)),
    unique_users=len(set(log.get('username', '') for log in logs if log.get('username'))),
    mobile_percentage=round((mobile_users / len(logs)) * 100, 1) if logs else 0,
    top_browsers=sorted(browsers.items(), key=lambda x: x[1], reverse=True)[:5],
    top_os=sorted(os_stats.items(), key=lambda x: x[1], reverse=True)[:5],
    top_actions=sorted(actions_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    )

@app.route('/add', methods=['POST'])
def add_item():
    try:
        username = request.form.get('username', '').strip()
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        client_ip = get_client_ip()

        # Validações
        if not username or username not in user_data:
            log_access(client_ip, "add_item_fail", username, "validation_error", 
                      {"error": "invalid_user"})
            return jsonify({"success": False, "message": "Usuário inválido"}), 400
            
        if not validar_titulo(title):
            log_access(client_ip, "add_item_fail", username, "validation_error", 
                      {"error": "invalid_title", "title": title})
            return jsonify({"success": False, "message": "Título inválido"}), 400
            
        if not validar_categoria(category):
            log_access(client_ip, "add_item_fail", username, "validation_error", 
                      {"error": "invalid_category", "category": category})
            return jsonify({"success": False, "message": "Categoria inválida"}), 400

        # Normalização
        title_clean = title.strip()
        title_normalizado = limpar_input(title)
        
        # Verificar duplicatas
        key = "movies" if category == "filme" else "series"
        lista = user_data[username][key]
        lista_normalizada = [limpar_input(t) for t in lista if isinstance(t, str)]

        if title_normalizado in lista_normalizada:
            log_access(client_ip, "add_item_fail", username, "duplicate", 
                      {"title": title_clean, "category": category})
            return jsonify({
                "success": False,
                "message": "Já existe esse título"
            }), 400

        # Adicionar
        lista.append(title_clean)
        save_data()
        
        # Log de sucesso com estatísticas
        log_access(client_ip, "add_item_success", username, "add_item", {
            "title": title_clean,
            "category": category,
            "new_total": len(lista),
            "library_stats": {
                "total_movies": len(user_data[username]["movies"]),
                "total_series": len(user_data[username]["series"])
            }
        })
        
        return jsonify({
            "success": True, 
            "message": f"{title_clean} adicionado com sucesso!"
        })
        
    except Exception as e:
        client_ip = get_client_ip()
        log_access(client_ip, "add_item_error", username, "system_error", 
                  {"error": str(e)})
        print(f"Erro em add_item: {e}")
        return jsonify({
            "success": False,
            "message": "Erro interno do servidor"
        }), 500


if __name__ == "__main__":
    if platform.system() == "Windows":
        os.system("mode con: cols=80 lines=25")
        os.system("title Gerenciador de Filmes e Séries")

    # Para funcionar no Replit
    app.run(host='0.0.0.0', port=3000)