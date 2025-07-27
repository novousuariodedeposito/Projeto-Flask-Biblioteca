
import sqlite3
import json
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="biblioteca.db"):
        self.db_path = db_path
        self.init_database()
        self.migrate_from_json()
    
    def get_connection(self):
        """Retorna uma conexão com o banco"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
        return conn
    
    def init_database(self):
        """Inicializa as tabelas do banco de dados"""
        conn = self.get_connection()
        try:
            # Tabela de usuários
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de filmes
            conn.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, title)
                )
            ''')
            
            # Tabela de séries
            conn.execute('''
                CREATE TABLE IF NOT EXISTS series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, title)
                )
            ''')
            
            # Tabela de itens em aberto
            conn.execute('''
                CREATE TABLE IF NOT EXISTS abertos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('filme', 'serie')),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, title, type)
                )
            ''')
            
            # Tabela de logs de acesso
            conn.execute('''
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    page TEXT NOT NULL,
                    username TEXT,
                    action TEXT,
                    method TEXT,
                    device_info TEXT,
                    extra_data TEXT
                )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def migrate_from_json(self):
        """Migra dados existentes do JSON para o banco de dados"""
        if not os.path.exists("media_lists.json"):
            return
            
        try:
            with open("media_lists.json", "r", encoding="utf-8") as file:
                user_data = json.load(file)
        except:
            return
            
        conn = self.get_connection()
        try:
            for username, data in user_data.items():
                # Criar usuário se não existir
                user_id = self.get_or_create_user(username, conn)
                
                # Migrar filmes
                for movie in data.get("movies", []):
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO movies (user_id, title) VALUES (?, ?)",
                            (user_id, movie)
                        )
                    except:
                        pass
                
                # Migrar séries
                for serie in data.get("series", []):
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO series (user_id, title) VALUES (?, ?)",
                            (user_id, serie)
                        )
                    except:
                        pass
                
                # Migrar abertos
                abertos = data.get("abertos", {})
                for movie in abertos.get("movies", []):
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO abertos (user_id, title, type) VALUES (?, ?, 'filme')",
                            (user_id, movie)
                        )
                    except:
                        pass
                        
                for serie in abertos.get("series", []):
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO abertos (user_id, title, type) VALUES (?, ?, 'serie')",
                            (user_id, serie)
                        )
                    except:
                        pass
            
            conn.commit()
            print("✅ Migração do JSON para SQLite concluída!")
        finally:
            conn.close()
    
    def get_or_create_user(self, username, conn=None):
        """Obtém ou cria um usuário"""
        close_conn = conn is None
        if conn is None:
            conn = self.get_connection()
            
        try:
            cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row:
                return row['id']
            else:
                cursor = conn.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    (username,)
                )
                conn.commit()
                return cursor.lastrowid
        finally:
            if close_conn:
                conn.close()
    
    def get_user_movies(self, username):
        """Retorna lista de filmes do usuário"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT m.title FROM movies m
                JOIN users u ON m.user_id = u.id
                WHERE u.username = ?
                ORDER BY m.added_at DESC
            ''', (username,))
            return [row['title'] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_user_series(self, username):
        """Retorna lista de séries do usuário"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT s.title FROM series s
                JOIN users u ON s.user_id = u.id
                WHERE u.username = ?
                ORDER BY s.added_at DESC
            ''', (username,))
            return [row['title'] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_user_abertos(self, username):
        """Retorna itens em aberto do usuário"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT title, type FROM abertos a
                JOIN users u ON a.user_id = u.id
                WHERE u.username = ?
                ORDER BY a.added_at DESC
            ''', (username,))
            
            result = {"movies": [], "series": []}
            for row in cursor.fetchall():
                if row['type'] == 'filme':
                    result["movies"].append(row['title'])
                else:
                    result["series"].append(row['title'])
            return result
        finally:
            conn.close()
    
    def add_item(self, username, title, category):
        """Adiciona um item (filme ou série)"""
        conn = self.get_connection()
        try:
            user_id = self.get_or_create_user(username, conn)
            
            if category == "filme":
                conn.execute(
                    "INSERT INTO movies (user_id, title) VALUES (?, ?)",
                    (user_id, title)
                )
            else:
                conn.execute(
                    "INSERT INTO series (user_id, title) VALUES (?, ?)",
                    (user_id, title)
                )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Item já existe
        finally:
            conn.close()
    
    def delete_item(self, username, title, category):
        """Remove um item"""
        conn = self.get_connection()
        try:
            if category == "filme":
                conn.execute('''
                    DELETE FROM movies WHERE user_id = (
                        SELECT id FROM users WHERE username = ?
                    ) AND LOWER(title) = LOWER(?)
                ''', (username, title))
            else:
                conn.execute('''
                    DELETE FROM series WHERE user_id = (
                        SELECT id FROM users WHERE username = ?
                    ) AND LOWER(title) = LOWER(?)
                ''', (username, title))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()
    
    def add_aberto(self, username, title, category):
        """Adiciona item em aberto"""
        conn = self.get_connection()
        try:
            user_id = self.get_or_create_user(username, conn)
            conn.execute(
                "INSERT INTO abertos (user_id, title, type) VALUES (?, ?, ?)",
                (user_id, title, category)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def delete_aberto(self, username, title, category):
        """Remove item em aberto"""
        conn = self.get_connection()
        try:
            conn.execute('''
                DELETE FROM abertos WHERE user_id = (
                    SELECT id FROM users WHERE username = ?
                ) AND LOWER(title) = LOWER(?) AND type = ?
            ''', (username, title, category))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()
    
    def move_to_biblioteca(self, username, title, category):
        """Move item de aberto para biblioteca"""
        conn = self.get_connection()
        try:
            user_id = self.get_or_create_user(username, conn)
            
            # Adiciona à biblioteca
            try:
                if category == "filme":
                    conn.execute(
                        "INSERT INTO movies (user_id, title) VALUES (?, ?)",
                        (user_id, title)
                    )
                else:
                    conn.execute(
                        "INSERT INTO series (user_id, title) VALUES (?, ?)",
                        (user_id, title)
                    )
            except sqlite3.IntegrityError:
                pass  # Já existe na biblioteca
            
            # Remove dos abertos
            conn.execute('''
                DELETE FROM abertos WHERE user_id = ? 
                AND LOWER(title) = LOWER(?) AND type = ?
            ''', (user_id, title, category))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def log_access(self, ip, page, username=None, action=None, method="GET", device_info=None, extra_data=None):
        """Registra log de acesso"""
        conn = self.get_connection()
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute('''
                INSERT INTO access_logs 
                (timestamp, ip, page, username, action, method, device_info, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, ip, page, username, action, method,
                json.dumps(device_info) if device_info else None,
                json.dumps(extra_data) if extra_data else None
            ))
            conn.commit()
            
            # Manter apenas os últimos 2000 logs
            conn.execute('''
                DELETE FROM access_logs WHERE id NOT IN (
                    SELECT id FROM access_logs ORDER BY id DESC LIMIT 2000
                )
            ''')
            conn.commit()
        finally:
            conn.close()
    
    def get_all_users(self):
        """Retorna lista de todos os usuários"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT username FROM users ORDER BY username")
            return [row['username'] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_access_logs(self, limit=50):
        """Retorna logs de acesso"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM access_logs 
                ORDER BY id DESC LIMIT ?
            ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                log = dict(row)
                if log['device_info']:
                    try:
                        log['device_info'] = json.loads(log['device_info'])
                    except:
                        log['device_info'] = {}
                if log['extra_data']:
                    try:
                        log['extra_data'] = json.loads(log['extra_data'])
                    except:
                        log['extra_data'] = {}
                logs.append(log)
            return logs
        finally:
            conn.close()
    
    def get_stats(self):
        """Retorna estatísticas do sistema"""
        conn = self.get_connection()
        try:
            stats = {}
            
            # Total de usuários
            cursor = conn.execute("SELECT COUNT(*) as count FROM users")
            stats['total_users'] = cursor.fetchone()['count']
            
            # Total de filmes
            cursor = conn.execute("SELECT COUNT(*) as count FROM movies")
            stats['total_movies'] = cursor.fetchone()['count']
            
            # Total de séries
            cursor = conn.execute("SELECT COUNT(*) as count FROM series")
            stats['total_series'] = cursor.fetchone()['count']
            
            # Total de abertos
            cursor = conn.execute("SELECT COUNT(*) as count FROM abertos")
            stats['total_abertos'] = cursor.fetchone()['count']
            
            # Total de logs
            cursor = conn.execute("SELECT COUNT(*) as count FROM access_logs")
            stats['total_logs'] = cursor.fetchone()['count']
            
            return stats
        finally:
            conn.close()

# Instância global do banco
db = Database()
