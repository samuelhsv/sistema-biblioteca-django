# Fixtures: dados de teste do sistema

## Para que serve
A homologação (o site de testes) começa com o banco vazio. Em vez de
cadastrar livros e alunos à mão toda vez, guardamos dados **inventados**
em arquivos do repositório e mandamos o sistema carregá-los com um comando.
Esses arquivos se chamam **fixtures**.

Este documento ensina a carregar os dados e a acrescentar dados novos
sem estragar os dos colegas.

## Regras de ouro
1. **Só dados inventados.** Nada de nome, RA, SIAPE ou e-mail de pessoa real (LGPD).
2. **Nunca carregar na produção.** O carregamento sobrescreve registros e
   apagaria dados reais.
3. **Todo registro tem `pk`** (explicado abaixo).

## Como é um arquivo de fixture
É um arquivo de texto no formato JSON: uma lista de blocos, e cada bloco é um registro.

```json
[
  {
    "model": "biblioteca.livro",
    "pk": 1,
    "fields": {
      "titulo": "Código Limpo",
      "capa": "",
      "categoria": 1,
      "qtd_total": 2,
      "qtd_disponivel": 2,
      "disponivel": true,
      "autores": [1]
    }
  },
  {
    "model": "biblioteca.categoria",
    "pk": 1,
    "fields": {
      "nome": "Tecnologia da Informação"
    }
  },
  {
    "model": "biblioteca.autor",
    "pk": 1,
    "fields": {
      "primeiro_nome": "Robert",
      "sobrenome": "Martin"
    }
  }
]
```

- `model`: de qual "tabela" é o registro (`nome-do-app.nome-do-modelo`, em minúsculas).
- `pk`: o número de identificação do registro (veja a próxima seção).
- `fields`: os campos, com os mesmos nomes do `models.py`.
- `"categoria": 1` quer dizer "a categoria de pk 1". É assim que um registro
  aponta para outro, então a categoria 1 precisa existir.

Na dúvida, copie o formato de um bloco que já existe na pasta.

## O que é o `pk` e por que importa
`pk` é o número que identifica um registro dentro da sua tabela: livro 1,
livro 2... Pense numa cadeira numerada. Ao carregar, o sistema senta cada
registro na cadeira indicada:

- cadeira vazia: o registro é criado;
- cadeira ocupada: o registro antigo é **substituído** pelo novo
  (por isso carregar duas vezes não duplica nada);
- bloco sem `pk`: o sistema cria uma cadeira nova a cada carga e os dados se duplicam.

O número só precisa ser único **dentro da mesma tabela**: livro 5 e categoria 5
convivem sem problema.

**O risco:** se duas pessoas criam, cada uma no seu computador, um livro de
pk 5, um apaga o outro no carregamento. Por isso cada arquivo tem uma
**faixa de números reservada**.

## Organização
Os arquivos ficam em `myproject/fixtures/` e são carregados em ordem
alfabética (por isso o número no começo do nome).

| Arquivo | Conteúdo | Faixa de pk |
|---|---|---|
| 01_base.json | categorias, autores, livros | 1 a 99 |
| 02_membros.json | alunos, professores e cursos | 100 a 199 |

Campos que não podem repetir (RA, SIAPE, e-mail) também não podem
repetir entre arquivos.


## Como acrescentar dados

Existem dois caminhos. O **A** (escrever à mão) é o mais simples para poucos
registros, uns 1 a 5. O **B** (cadastrar no admin e exportar) compensa quando
são muitos registros ou muitos campos.

### Em qualquer caminho, comece assim
1. Atualize a `develop` e crie uma branch: `chore/CODIGO-fixture-assunto`.
2. Decida onde seus dados vão ficar:
   - assunto que já tem arquivo: use esse arquivo, com `pk` dentro da faixa dele;
   - assunto novo: crie o próximo arquivo (`03_assunto.json`) e **reserve a faixa
     na tabela da seção "Organização"**, no mesmo PR.

### Caminho A: escrever à mão
1. Abra um arquivo existente e copie um bloco do mesmo modelo.
2. Troque o `pk` por um número livre da faixa (olhe o maior `pk` daquele modelo
   e some 1) e troque os campos.
3. Se o bloco aponta para outro registro (`"categoria": 1`), confira se esse
   registro existe neste arquivo ou em outro.

### Caminho B: cadastrar no admin e exportar

**B1. Prepare um banco local limpo.** Os números que ligam um registro a outro
(ex.: `"categoria": 3`) só fazem sentido dentro do mesmo conjunto de dados.
No seu banco, a categoria 3 pode ser uma; na fixture, outra. Para os números
baterem, comece de um banco com exatamente o conteúdo das fixtures:
```bash
cd myproject
mv db.sqlite3 db-meu-backup.sqlite3        # guarda o seu banco de lado
python manage.py migrate                   # cria um banco novo e vazio
python manage.py loaddata fixtures/*.json  # coloca nele os dados das fixtures
python manage.py createsuperuser           # para poder entrar no admin
```
Se `db-meu-backup.sqlite3` já existir, não rode o mv: ele sobrescreveria o seu backup com o banco novo


**B2. Cadastre os dados novos no admin local** (`python manage.py runserver`).
Tudo inventado.

**B3. Descubra o `pk` dos registros que você criou.** Dois jeitos:
- No admin, clique no registro. O número na barra de endereço é o `pk`:
  `.../admin/biblioteca/livro/7/change/` quer dizer `pk` 7.
- Ou no terminal, rode `python manage.py shell` e depois:
  ```python
  from biblioteca.models import Livro
  Livro.objects.values_list("pk", "titulo")
  ```
  Aparece a lista de pares (`pk`, título). Anote os dos registros novos.
  Para sair do shell, digite `exit()`.

**B4. Exporte só os registros novos:**
```bash
python manage.py dumpdata biblioteca.Livro --pks 7,8 --indent 2 -o fixtures/03_livros_novos.json
```
| Parte | O que significa |
|---|---|
| `dumpdata` | "exporte dados do banco para texto" |
| `biblioteca.Livro` | de qual modelo (`nome-do-app.NomeDoModelo`, como no `models.py`) |
| `--pks 7,8` | só os registros com esses números (separados por vírgula, **sem espaço**) |
| `--indent 2` | deixa o arquivo legível, com recuo de 2 espaços |
| `-o fixtures/...` | grava nesse arquivo, em vez de mostrar na tela |

- Para entender o que o comando faz, rode primeiro **sem** o `-o ...`: o
  resultado aparece na tela e nada é gravado.
- O `-o` **sobrescreve** o arquivo se ele já existir. Use um nome novo.
- O `--pks` só funciona com **um modelo por vez**. Se você criou livros e
  autores, rode o comando duas vezes, cada um gravando num arquivo
  (e liste cada arquivo na tabela "Organização").
- Se o livro tem autores, o arquivo mostra `"autores": [2, 3]`. São números
  de autores que precisam existir nas fixtures.
- Para juntar ao arquivo que já existe: copie os blocos do arquivo novo para
  dentro da lista do arquivo antigo (cada bloco termina com `},`, exceto o
  último da lista, que termina com `}`) e apague o arquivo novo. Confira com o
  `json.tool` depois.

**B5. Ajuste os números para a faixa reservada.** Abra o arquivo no VS Code. Se
os `pk` não estão dentro da faixa do seu arquivo (tabela "Organização"), troque:
- use Localizar e Substituir (`Ctrl+H`) e **inclua a vírgula**: troque
  `"pk": 7,` por `"pk": 200,`. Sem a vírgula, trocaria também `"pk": 70,`;
- se outro registro novo aponta para este, troque lá também
  (ex.: `"curso": 7` vira `"curso": 200`).

### Conferir (vale para os dois caminhos)
1. Confira se o JSON está bem escrito:
   `python -m json.tool fixtures/ARQUIVO.json > /dev/null`
   Se não imprimir nada, está válido. Se imprimir erro, ele indica a linha
   (quase sempre é vírgula sobrando ou faltando).
2. Carregue o arquivo: `python manage.py loaddata fixtures/ARQUIVO.json`
   Deve aparecer algo como `Installed 2 object(s) from 1 fixture(s)`.
3. Abra o admin e confira os dados. Procure nomes reais.
4. Se usou o Caminho B, devolva o seu banco ao lugar:
   `mv db-meu-backup.sqlite3 db.sqlite3`
5. Faça o commit e o PR. Quem revisa lê o arquivo atrás de dado real e de
   `pk` repetido.

## Cuidado com estoque e empréstimos
O carregamento grava os valores **exatamente como estão no arquivo**. Ele não
executa o cálculo automático do sistema. Por isso, campos que o sistema
costuma calcular sozinho (`qtd_disponivel`, `disponivel`, datas de devolução)
precisam já estar corretos no arquivo.

**Recomendação: não coloque empréstimos nas fixtures.** Crie os empréstimos
pelo admin da homologação, como no roteiro de homologação (H-03). Assim o
cálculo do sistema é testado de verdade.

Se mesmo assim um empréstimo ativo for necessário, o livro dele precisa ter
`qtd_disponivel` já descontado (`qtd_total` menos os empréstimos ativos) e
`disponivel` coerente com isso.

## Quando alguém muda um modelo
Se um modelo ganha um campo obrigatório (ex.: curso do aluno), os dados
antigos das fixtures ficam desatualizados. O carregamento **não confere as
regras do sistema**: ele carrega o dado inválido sem reclamar, e o erro só
aparece depois, quando alguém tenta editar o registro no admin.

Por isso, o PR que muda um modelo também atualiza os blocos afetados das fixtures.

## Como carregar na homologação
```bash
cd ~/sistema-biblioteca-django
source ~/.virtualenvs/.venv/bin/activate
git pull origin develop
cd myproject
python manage.py migrate
python manage.py loaddata fixtures/*.json
```
O que cada passo faz:
- `git pull`: traz os arquivos de fixture mais recentes;
- `migrate`: cria/atualiza as tabelas. **Precisa vir antes**, porque o
  carregamento só preenche tabelas, não as cria;
- `loaddata fixtures/*.json`: carrega todos os arquivos da pasta, na ordem
  alfabética. Sucesso: `Installed N object(s) from M fixture(s)`.

Depois, abra o admin da homologação e confira se os dados apareceram.
Se o banco foi recriado do zero, rode também `python manage.py createsuperuser`.

**Atenção:** carregar de novo **desfaz** edições manuais feitas nos registros
da fixture. Para testes manuais na homologação, crie registros com `pk`
fora das faixas reservadas.

## Se der erro

| O que aparece | O que significa | O que fazer |
|---|---|---|
| `DeserializationError` ou `Problem installing fixture` | O arquivo está mal escrito ou tem um nome de campo/modelo errado | Rode o `json.tool` (seção Conferir, passo 1) e compare os nomes com o `models.py` |
| `IntegrityError` com `invalid foreign key` | Um registro aponta para outro que não existe (ex.: `"categoria": 7`) | Crie o registro apontado ou corrija o número |
| `UNIQUE constraint failed` | Um campo que não pode repetir (RA, e-mail) já existe em outro registro | Troque o valor por um inédito |
| `No fixture named ... found` | O comando não achou o arquivo | Confira com `pwd` se está em `myproject/` e se o nome está certo |