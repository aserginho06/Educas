# Educas

Refatoracao do Educas para uma plataforma educacional moderna em Django, com RBAC, API versionada e separacao clara de dominio.

## Stack

- Django
- Django REST Framework
- JWT
- PostgreSQL
- Docker

## Apps

- `core`: camada web publica e paginas institucionais.
- `accounts`: usuario customizado, perfis e RBAC.
- `academics`: turmas, materias, matriculas, notas, faltas e eventos.
- `engagement`: feed academico, comentarios e reacoes.
- `assignments`: atividades e entregas.
- `api`: roteamento e paginacao da API `v1`.

## Ambiente local

1. Copie `.env.example` para `.env`.
2. Instale as dependencias de `requirements.txt`.
3. Rode `python manage.py makemigrations`.
4. Rode `python manage.py migrate`.
5. Crie um superusuario com `python manage.py createsuperuser`.
6. Suba o servidor com `python manage.py runserver`.

## Docker

```powershell
docker compose up --build
```

## Endpoints principais

- Site: `http://127.0.0.1:8000/`
- Admin Django: `http://127.0.0.1:8000/admin/`
- API: `http://127.0.0.1:8000/api/v1/`
- JWT: `http://127.0.0.1:8000/api/v1/auth/token/`
