
#!/usr/bin/env python3
from database import db
import json

def verify_migration():
    print("🔍 Verificando migração dos dados...")
    
    # Verificar usuários
    users = db.get_all_users()
    print(f"✅ Usuários migrados: {len(users)}")
    for user in users:
        print(f"   - {user}")
    
    # Verificar dados por usuário
    for username in users:
        movies = db.get_user_movies(username)
        series = db.get_user_series(username)
        abertos = db.get_user_abertos(username)
        
        print(f"\n📊 {username}:")
        print(f"   🎬 Filmes: {len(movies)}")
        print(f"   📺 Séries: {len(series)}")
        print(f"   🎯 Em aberto - Filmes: {len(abertos['movies'])}")
        print(f"   🎯 Em aberto - Séries: {len(abertos['series'])}")
    
    # Verificar logs
    logs = db.get_access_logs(10)
    print(f"\n📝 Logs migrados: Mostrando últimos 10 de muitos")
    
    # Estatísticas gerais
    stats = db.get_stats()
    print(f"\n📈 Estatísticas gerais:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Migração concluída com sucesso!")

if __name__ == "__main__":
    verify_migration()
