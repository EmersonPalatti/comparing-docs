# Deploy no Streamlit Cloud

## 1. Publicar o repositorio

Suba este projeto para um repositorio no GitHub.

O arquivo real `.streamlit/secrets.toml` nao deve ser commitado. Ele esta no `.gitignore`.

## 2. Criar o app no Streamlit Cloud

No Streamlit Cloud:

1. Crie um novo app.
2. Selecione o repositorio.
3. Configure o arquivo principal como:

```text
src/app.py
```

## 3. Configurar login em Secrets

Em `Settings > Secrets`, configure:

```toml
[auth]
username = "admin"
password = "vaidartudocerto"
```

## 4. Rodar localmente com login

Opcao 1: variaveis de ambiente no PowerShell:

```powershell
$env:APP_USERNAME="admin"
$env:APP_PASSWORD="vaidartudocerto"
uv run streamlit run src/app.py
```

Opcao 2: criar um arquivo local `.streamlit/secrets.toml` com:

```toml
[auth]
username = "admin"
password = "vaidartudocerto"
```

Esse arquivo local nao deve ser enviado ao GitHub.

## Observacao de seguranca

Este login e uma protecao simples para um MVP. Ele nao substitui um sistema completo de autenticacao com usuarios, recuperacao de senha e permissoes.
