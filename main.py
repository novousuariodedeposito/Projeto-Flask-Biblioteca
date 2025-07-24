import json
from flask import Flask, render_template, request, render_template_string, redirect, url_for, jsonify
import os
import platform
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


def limpar_input(texto):
    return texto.strip().lower()


@app.route('/')
def index():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if not username:
            return "Usuário não pode ser vazio!"
        if username not in user_data:
            user_data[username] = {
                "movies": [],
                "series": [],
                "em_aberto": {
                    "movies": [],
                    "series": []
                }
            }
            save_data()
        return redirect(url_for('my_biblioteca', username=username))

    return render_template('login.html')


@app.route('/mybiblioteca', methods=['GET'])
def my_biblioteca():
    username = request.args.get('username')
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

    if username in user_data:
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
        save_data()
        return jsonify({"success": True})
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
    username = request.form.get('username')
    title = request.form.get('title', '').strip()
    category = request.form.get('category')

    if not title:
        return jsonify({"success": False, "message": "Título vazio"}), 400

    if username not in user_data or category not in ["filme", "serie"]:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    key = "movies" if category == "filme" else "series"

    user_data.setdefault(username, {})
    user_data[username].setdefault("abertos", {"movies": [], "series": []})

    if title not in user_data[username]["abertos"][key]:
        user_data[username]["abertos"][key].append(title)
        save_data()
        return jsonify({"success": True, "message": "Adicionado com sucesso"})
    else:
        return jsonify({"success": False, "message": "Item já existe"}), 400


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


@app.route('/add', methods=['POST'])
def add_item():
    username = request.form.get('username')
    title = request.form.get('title', '').strip()
    category = request.form.get('category')

    if not title:
        return jsonify({"success": False, "message": "Título vazio"}), 400

    title_clean = title.strip()
    title_normalizado = limpar_input(title)

    if username in user_data:
        lista = user_data[username][
            "movies"] if category == "filme" else user_data[username]["series"]
        lista_normalizada = [limpar_input(t) for t in lista]

        if title_normalizado in lista_normalizada:
            return jsonify({
                "success": False,
                "message": "Já existe esse título"
            }), 400

        lista.append(title_clean)
        save_data()
        return jsonify({"success": True, "message": "Adicionado com sucesso"})

    return jsonify({
        "success": False,
        "message": "Usuário não encontrado"
    }), 400


if __name__ == "__main__":
    if platform.system() == "Windows":
        os.system("mode con: cols=80 lines=25")
        os.system("title Gerenciador de Filmes e Séries")

    # Para funcionar no Replit
    app.run(host='0.0.0.0', port=3000)