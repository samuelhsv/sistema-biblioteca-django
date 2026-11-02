# Deploy

## 1. Visão geral
| Ambiente | Branch | Endereço | Conta PythonAnywhere |
|---|---|---|---|
| Homologação | develop | fluihomolog.pythonanywhere.com | fluihomolog |
| Produção | main | bibliotecaflui.pythonanywhere.com | bibliotecaflui |

## 2. Pré-requisitos
- Acesso à conta (senha no gerenciador de senhas do grupo, nunca aqui)
- Na aba Web, o campo _Virtualenv_ deve apontar para `~/.virtualenvs/.venv`
- Projeto em `~/sistema-biblioteca-django`, venv em `~/.virtualenvs/.venv`
- `.env` já existe no servidor, em `myproject/.env`

### Como abrir o terminal do PythonAnywhere

1. Entre em pythonanywhere.com com a conta do ambiente (homologação: `fluihomolog`; produção: `bibliotecaflui`).
2. No menu superior, clique em **Consoles**.
3. Em "Start a new console", clique em **Bash**. (Se já houver um console
   aberto na lista "Your consoles", pode reutilizá-lo.)
4. Aparece uma tela preta com um prompt parecido com `12:34 ~ $`.
   Os comandos digitados ali rodam no servidor, não no seu computador.

**Antes de rodar qualquer coisa, confira onde você está:**

- `pwd` mostra a pasta atual. Os comandos `python manage.py ...` só funcionam
  dentro de `myproject/`.
- Depois do `source .../activate`, o prompt ganha um prefixo como `(.venv)`.
  Se não aparecer, o venv não está ativo.
- `git branch` mostra a branch atual com um `*`: deve ser `develop` na
  homologação e `main` na produção.

**Como executar os comandos das seções 3 e 4:**

- Copie e cole **um bloco de cada vez** e leia a saída antes de seguir.
- Se algum comando mostrar erro, **pare** e vá para a seção 6. O terminal não
  para sozinho: ao colar várias linhas, as seguintes continuam rodando mesmo
  que uma tenha falhado.
- Na produção, rode linha por linha pelo menos até o `migrate`. Se o `cp` do
  backup falhar e você seguir para o `migrate`, perdeu a rede de segurança.
- O último passo (Reload) **não** é no terminal: é na aba **Web**.

## 3. Atualizar a homologação
(Na homologação não há backup: se o banco quebrar, apague o `db.sqlite3` e recrie com `migrate`, `loaddata` e `createsuperuser`)
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

Para a verificação completa, rode o [roteiro de homologação](docs/ROTEIRO_HOMOLOGACAO.md)

## 6. Se der errado

**Regra de ouro:** se o `migrate` falhar, **não clique em Reload**.
O código novo já está no disco (o `git pull` já rodou) e o banco ainda está no esquema antigo. Recarregar faria o site rodar código novo sobre banco antigo. O processo em execução ainda tem o código antigo na memória e, em geral, continua funcionando, mas o estado é frágil: resolva rápido.

Os comandos desta seção que usam `manage.py` ou `db.sqlite3` rodam dentro de `myproject/`.

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

## 7. Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| Página mostra "Bad Request (400)" | O endereço acessado não está em `ALLOWED_HOSTS` no `.env` do servidor | Ver a causa exata em Web → Error log. Corrigir `ALLOWED_HOSTS` no `.env` (sem espaços depois das vírgulas) e dar Reload |
| Admin aparece sem CSS | O mapeamento de arquivos estáticos não estava configurado na aba Web | Web → Static files: URL `/static/` → pasta do `STATIC_ROOT`; rodar `collectstatic`; Reload |
| Mudança no código não aparece | Faltou o Reload | Aba Web → Reload |
| `ModuleNotFoundError` | Venv errado ou biblioteca nova fora do `requirements.txt` | Ativar o venv certo; `pip install -r requirements.txt` |

## 8. Renovação mensal das contas gratuitas

As contas gratuitas do PythonAnywhere desligam o site se ninguém renovar
dentro de 1 mês. Isso vale para **homologação e produção**.

**Como renovar** (leva 1 minuto):
1. Entre na conta (senha no cofre do grupo).
2. Aba **Web** → botão **Run until 1 month from today**.
3. Confirme que a data de expiração mudou.
4. Repita para a outra conta.

**Lembrete:** agenda "Renovar contas PythonAnywhere (FLUI)" no Google Agenda, evento a cada 3 semanas
(a agenda aparece em ‘Outras agendas’ para quem aceitou o convite). Todos recebem o alerta.

**Responsável:** Samuel. **Reserva:** Lilian.

Quem renova responde no grupo: "renovei, expira em DD/MM".
Se não houver confirmação até 24 h depois do lembrete, a reserva renova.

**Se o site já saiu do ar:** entre na conta e clique no mesmo botão; o site deve voltar. Depois, descubra por que o lembrete falhou.

**Prazo do projeto:** última renovação em 13/12, antes da apresentação de 17/12.