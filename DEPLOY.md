# Deploy

## 1. Visão geral
| Ambiente | Branch | Endereço | Conta PythonAnywhere |
|---|---|---|---|
| Homologação | develop | fluihomolog.pythonanywhere.com | fluihomolog |
| Produção | main | bibliotecaflui.pythonanywhere.com | bibliotecaflui |

## 2. Pré-requisitos
- Acesso à conta (senha no gerenciador de senhas do grupo, nunca aqui)
- Projeto em `~/sistema-biblioteca-django`, venv em `~/.virtualenvs/.venv`
- `.env` já existe no servidor, em `myproject/.env`

## 3. Atualizar a homologação
```bash
cd ~/sistema-biblioteca-django
source ~/.virtualenvs/.venv/bin/activate
git pull origin develop
pip install -r requirements.txt
cd myproject
python manage.py migrate
python manage.py collectstatic --noinput
```
Depois: aba **Web** → botão **Reload**.

## 4. Atualizar a produção
(igual à seção 3, mas com `main`, e **backup antes do migrate**)
```bash
cd ~/sistema-biblioteca-django
source ~/.virtualenvs/.venv/bin/activate
git pull origin main
pip install -r requirements.txt
cd myproject
mkdir -p backups
cp db.sqlite3 backups/db-$(date +%F).sqlite3
python manage.py migrate
python manage.py collectstatic --noinput
```
Depois: aba **Web** → botão **Reload**.


## 5. Como verificar
- [ ] A página inicial (`/`) abre sem erro
- [ ] `/admin/` abre **com estilo** (fundo azul no cabeçalho, não texto cru)
- [ ] É possível entrar no admin com um usuário de teste
- [ ] A lista de livros aparece (confirma que o banco está ok)
- [ ] Aba **Web → Error log**: nenhum erro novo depois do Reload

## 6. Se der errado

**Regra de ouro:** se o `migrate` falhar, **não clique em Reload**. O site continua
rodando o código antigo, que em geral continua funcionando, mas o estado é frágil: resolva rápido. Resolva antes de recarregar.

1. Leia a **última linha** do erro do terminal. Ela diz o tipo do problema.
2. Veja o estado das migrações: `python manage.py showmigrations`
   (`[X]` = aplicada, `[ ]` = pendente).
3. Se não der para corrigir na hora, **volte tudo ao estado anterior**
   (dentro de `myproject/`, onde estão o `manage.py` e o `db.sqlite3`):
   - descubra o commit anterior: `git log --oneline -5`
   - volte o código: `git checkout <hash-do-commit-anterior>`
   - restaure o banco: `cp backups/db-AAAA-MM-DD.sqlite3 db.sqlite3`
   - clique em **Reload**
4. **Depois que o problema for corrigido no repositório**, saia do estado
   "sem branch" antes de atualizar de novo:
   `git checkout develop` (ou `main` em produção) e então `git pull`.
5. Avise o grupo e abra uma issue `tipo:bug` com a mensagem de erro completa.

> O backup é feito **antes** do `migrate` porque o `migrate` altera o banco.
> Um backup feito depois já contém a alteração, então não serve para voltar atrás.

> Os comandos `cp` e `showmigrations` precisam rodar em myproject/ (onde estão o manage.py e o db.sqlite3)

## 7. Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| Página mostra "Bad Request (400)" | O endereço acessado não está em `ALLOWED_HOSTS` no `.env` do servidor | Ver a causa exata em Web → Error log. Corrigir `ALLOWED_HOSTS` no `.env` (sem espaços depois das vírgulas) e dar Reload |
| Admin aparece sem CSS | O mapeamento de arquivos estáticos não estava configurado na aba Web | Web → Static files: URL `/static/` → pasta do `STATIC_ROOT`; rodar `collectstatic`; Reload |
| Mudança no código não aparece | Faltou o Reload | Aba Web → Reload |
| `ModuleNotFoundError` | Venv errado ou biblioteca nova fora do `requirements.txt` | Ativar o venv certo; `pip install -r requirements.txt` |