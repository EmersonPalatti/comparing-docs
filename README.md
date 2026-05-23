# Comparing Docs

MVP local para comparar disciplinas entre dois documentos academicos e sugerir possiveis equivalencias para revisao humana.

Este projeto nao toma decisoes academicas oficiais. Ele gera uma analise automatizada de similaridade baseada nos documentos enviados.

## Como executar

```powershell
uv run streamlit run src/app.py
```

Para acessar a UI, configure login local por variaveis de ambiente:

```powershell
$env:APP_USERNAME="usuario-seguro"
$env:APP_PASSWORD="senha-forte-com-pelo-menos-12-caracteres"
uv run streamlit run src/app.py
```

No Streamlit Cloud, configure as credenciais em Secrets. Veja [README_DEPLOY.md](README_DEPLOY.md).

Na interface:

1. Envie os dois documentos.
2. Clique em `Extrair disciplinas`.
3. Revise as tabelas extraidas lado a lado, ajustando `Disciplina` e `Carga Horaria` se necessario.
4. Clique em `Comparar disciplinas revisadas`.
5. Use os filtros de classificacao, alerta e revisao manual.
6. Marque `Selecionar` nos pares que devem entrar no relatorio final.
7. Preencha `Observação do revisor` quando quiser registrar uma justificativa humana.
8. Baixe os arquivos Excel resumido, detalhado, o relatorio selecionado em Excel ou o relatorio selecionado em PDF.

A tabela de resultado inclui `Prioridade` e `Alertas`, com formatacao condicional na interface para facilitar a leitura.

## Testes

```powershell
uv run pytest
```

Sem `uv`, rode:

```powershell
python -m pytest
```

## Arquivos suportados no MVP

- PDF com texto selecionavel
- XLSX/XLS
- CSV
- TXT/MD

PDFs escaneados sem texto selecionavel retornam uma mensagem clara. OCR nao faz parte deste MVP.

## Segurança

- Consulte [README_DEPLOY.md](README_DEPLOY.md) para política de credenciais e dependências.
- Consulte [SECURITY_DEPLOY_CHECKLIST.md](SECURITY_DEPLOY_CHECKLIST.md) para checklist operacional de release.
- Consulte [SECURITY_REASSESSMENT.md](SECURITY_REASSESSMENT.md) para o resumo de reavaliação de risco.
