import os

# Le fichier DB principal est dans /instance/brainburst.db
# Mais l'app utilise aussi brainburst.db à la racine comme fallback
DB_INSTANCE = os.path.join('instance', 'brainburst.db')
DB_ROOT = 'brainburst.db'

deleted_any = False

for path in [DB_INSTANCE, DB_ROOT]:
    if os.path.exists(path):
        os.remove(path)
        print(f'✅ Supprimé : {path}')
        deleted_any = True
    else:
        print(f'ℹ️ Introuvable : {path}')

if deleted_any:
    print('\n🧹 Base de données réinitialisée. Relancez l\'application pour en créer une nouvelle.')
else:
    print('\n⚠️  Aucune base de données trouvée à supprimer.')

