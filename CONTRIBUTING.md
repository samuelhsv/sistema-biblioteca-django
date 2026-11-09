# O que é esse arquivo?
`CONTRIBUTING.md` contém guias de boas práticas para nomeação de branches, criação de commits e revisão de pull requests  

---

## Fluxo de trabalho 
```bash
# 1. Atualize sua develop local (para partir da versão mais recente da equipe)
git checkout develop
git pull origin develop

# 2. Crie a branch da tarefa: tipo/CODIGO-descricao-curta, sem acentos
#    (-b = cria e já entra nela)
git checkout -b feat/CAD-01-curso-periodo-aluno

# 3. Trabalhe e faça commits pequenos e frequentes
git status                      # SEMPRE confira o que vai entrar no commit
git add caminho/do/arquivo.py   # escolhe o que entra no commit
git commit -m "feat(membro): adiciona campos curso e periodo (CAD-01)"

# 4. Antes de abrir o PR, traga as novidades da develop para a sua branch
#    (outras pessoas podem ter mergeado enquanto você trabalhava) e rode os testes
git pull origin develop         # se aparecer conflito, resolva (ou peça ajuda)
python manage.py test

# 5. Envie a branch para o GitHub (-u liga a branch local à remota)
git push -u origin feat/CAD-01-curso-periodo-aluno
```

---

## Nome de branch

Formato: `tipo/CODIGO-descricao-curta`, sem acentos e com hífens no lugar de espaços.

O `tipo` é o mesmo da tabela de [Tipos](#tipos) (`feat`, `fix`, `docs`, `test`, `chore`).

| ✅ Certo | ❌ Errado | Por quê |
|---|---|---|
| `feat/CAD-01-curso-periodo-aluno` | `CAD-01` | sem tipo nem descrição |
| `docs/GOV-02-contributing` | `docs/GOV-02 contributing` | espaço no nome |
| `fix/RST-02-estoque-atraso` | `fix/RST-02-estoque-atraso-é-ao-devolver` | acento e descrição longa |

---

## Mensagens de commit (Conventional Commits)

Usamos o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/).
Ele deixa o histórico legível: só de ler a primeira linha, dá para saber **o que mudou** e **em qual parte do sistema**.

### Formato

```
tipo(escopo): descrição curta (CÓDIGO)
```

| Parte | O que é | Exemplo |
|---|---|---|
| **tipo** | A natureza da mudança (tabela abaixo) | `feat` |
| **escopo** | A parte do sistema afetada, entre parênteses | `membro`, `emprestimo`, `reservas`, `portal`, `readme` |
| **descrição** | O que a mudança faz, em uma linha | `adiciona campos curso e periodo` |
| **CÓDIGO** | A tarefa do backlog, entre parênteses, no final | `(CAD-01)` |

### Tipos

| Tipo | Use quando... | Exemplo |
|---|---|---|
| `feat` | o sistema ganha algo **novo** | `feat(membro): adiciona campos curso e periodo (CAD-01)` |
| `fix` | você corrige um comportamento **errado** | `fix(emprestimo): corrige estoque ao marcar atraso (RST-02)` |
| `docs` | só documentação, sem mudar o comportamento | `docs(readme): explica como rodar localmente` |
| `test` | só testes | `test(membro): cobre validacao de curso e periodo (CAD-01)` |
| `chore` | manutenção: dependências, configuração | `chore(deps): adiciona django-simple-history (AUD-01)` |

> O critério é **o que a mudança faz pelo sistema**, não a quantidade de código alterado.

### Regras da equipe

1. **Um commit = uma ideia.** Se a descrição precisa de "e" para explicar, provavelmente são dois commits.
2. **Verbo no presente** ("adiciona", "corrige", "remove"), sempre.
3. **Letra minúscula** no começo da descrição, **sem ponto final**.
4. **Sem acentos no tipo e no escopo** para não dar problema em terminais antigos.
5. **Sempre o código da tarefa** no final, para rastrear o commit até a issue.
6. **O mesmo tipo vale para a branch:** `feat/CAD-01-curso-periodo-aluno`.

### Bom e ruim

| ❌ Evite | ✅ Prefira | Por quê |
|---|---|---|
| `ajustes` | `fix(emprestimo): corrige data prevista ao renovar (RST-03)` | não diz o quê nem onde |
| `feat: muita coisa` | dois commits separados, cada um com seu escopo | mistura ideias |
| `Fix: Corrigi o bug.` | `fix(reservas): impede reserva duplicada (RES-02)` | tempo verbal, maiúscula, ponto final |
| `feat(membro): adiciona curso` *(sem código)* | `feat(membro): adiciona curso (CAD-01)` | perde o rastreio da tarefa |

---

## Como revisar um Pull Request

Revisar não é só procurar erro: é garantir que o código funciona, que outra pessoa
consegue entendê-lo daqui a um mês e que a equipe inteira conhece o que entrou no sistema.
Quem revisa cada frente está na tabela de rodízio do `BACKLOG_FLUI.md` (seção 2).

### 1. Baixe a branch e rode no seu computador

Ler o código no GitHub não basta: rode-o.

```bash
git fetch origin
git checkout feat/CAD-01-curso-periodo-aluno   # a branch do PR
pip install -r requirements.txt                # caso tenha biblioteca nova
python manage.py migrate
python manage.py makemigrations --check --dry-run   # não pode faltar migração
python manage.py test
python manage.py runserver                     # teste a funcionalidade na mão
```

### 2. Confira, nesta ordem

- [ ] Cada **critério de aceite** da issue está atendido (abra a issue ao lado do PR)
- [ ] A funcionalidade funciona na prática, **incluindo um caso de erro** (dado inválido, usuário sem permissão)
- [ ] Toda regra de negócio nova tem **teste**, e os testes passam
- [ ] As **migrações** estão no PR
- [ ] Nome da branch e mensagens de commit seguem este documento
- [ ] Não há nada sensível: senhas, `.env`, `db.sqlite3`
- [ ] O PR faz **uma tarefa só** e tem `Closes #<número>` na descrição
- [ ] O código é legível: nomes claros, sem trechos comentados ou sobras de depuração (`print`)

### 3. Escreva os comentários

- Comente **a linha específica**, não só o PR inteiro.
- Explique o **porquê** e, quando puder, sugira uma alternativa concreta.
- Prefira perguntas a ordens: "o que acontece se o membro não tiver e-mail aqui?"
- Elogie o que ficou bom. Também é feedback.
- Separe o que **bloqueia** do que é **sugestão**: marque o segundo com o prefixo `Sugestão:`.

| ❌ Evite | ✅ Prefira |
|---|---|
| "Isso está errado." | "Se `curso` vier vazio, o `clean()` não é chamado por `create()`. Dá para cobrir isso com `full_clean()` no teste?" |
| "Refaz isso." | "Sugestão: extrair essa conta para um método facilita testar." |

### 4. Decida e finalize

Na aba **Files changed → Review changes**, escolha uma opção:

| Opção | Quando |
|---|---|
| **Comment** | você só tem dúvidas e ainda não decidiu |
| **Approve** | os itens do passo 2 estão ok (pendências só de "Sugestão:") |
| **Request changes** | algum critério de aceite ou item do passo 2 falhou |

Depois de **Request changes**, quem fez o PR corrige com novos commits **na mesma branch**, e quem revisa olha de novo.

### 5. Merge

Com aprovação **e** verificação automática (CI) verde, quem fez o PR dá o merge, preferencialmente com **Squash and merge**. Quem revisa não dá merge no PR dos outros sem combinar.
