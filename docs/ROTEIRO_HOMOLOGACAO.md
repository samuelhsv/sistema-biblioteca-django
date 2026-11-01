# Roteiro de Homologação

Checklist de testes manuais, executado no ambiente de homologação
(fluihomolog.pythonanywhere.com), para verificar se o sistema **implantado**
funciona. Complementa os testes automatizados (`python manage.py test`), que
verificam o código, mas não o servidor real (estáticos, e-mail, banco).

- **Quando rodar:** no fim de cada sprint, antes do PR `develop → main`, e na FIN-01.
- **Quem roda:** cada pessoa testa a frente de outra.
- **Como registrar:** copie a tabela para uma issue (as caixinhas funcionam lá)
  e preencha o resultado.
- **Se algo falhar:** abra uma issue `tipo:bug` com o ID do item, o que
  aconteceu e o que era esperado.
- **Como manter:** toda tarefa nova acrescenta seus itens neste arquivo, no
  mesmo PR (faz parte da Definição de Pronto).

**Ambiente:** fluihomolog.pythonanywhere.com

**Commit testado:** ______  **Data:** ______  **Quem testou:** ______

## Pré-condições
- Fixture `dados_teste.json` carregada (dados fictícios)
- Superusuário de teste criado (senha no gerenciador de senhas, nunca aqui)

| ID | Fluxo | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| H-01 | Login no admin | Abrir `/admin/` e entrar | Painel abre **com estilo** | ☐ |
| H-02 | Cadastrar livro | Criar livro com qtd_total = 2 | Salva; `qtd_disponivel` = 2 | ☐ |
| H-03 | Empréstimo | Anotar `qtd_disponivel`; criar empréstimo | Diminui em 1 | ☐ |
| H-04 | Devolução | Marcar o empréstimo como devolvido | Volta ao valor anotado | ☐ |
| H-05 | Sem estoque | Emprestar livro com `qtd_disponivel` = 0 | Recusado com mensagem clara | ☐ |
| H-06 | Validação | Criar aluno sem RA; professor sem SIAPE | Erro no campo, não salva | ☐ |

## Falhas encontradas
(cada falha vira uma issue `tipo:bug`; anote aqui o número)