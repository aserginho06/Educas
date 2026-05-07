# Educas Django

Sistema Educas estruturado em Django com paginas do app, painel administrativo visual e Django Admin.

## Rodar localmente

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Depois acesse:

- App: http://127.0.0.1:8000/
- Feed: http://127.0.0.1:8000/feed.html
- Administrador Educas: http://127.0.0.1:8000/administrador.html
- Django Admin: http://127.0.0.1:8000/admin/

## Acesso de desenvolvimento

- Usuario: `admin`
- Senha: `admin123`

## Estrutura

- `educas/`: configuracao do projeto Django.
- `core/`: app principal com models, views, rotas, admin e seed.
- `templates/core/`: paginas HTML do sistema.
- `assets/`: CSS, JS e imagens servidos como arquivos estaticos.
- `db.sqlite3`: banco local de desenvolvimento.
