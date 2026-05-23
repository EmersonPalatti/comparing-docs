# Deploy e Segurança Operacional

## Credenciais em produção

- **Nunca** use credenciais padrão (`admin`, `password`, `123456`, similares).
- Configure `APP_USERNAME` e `APP_PASSWORD` **somente** no gerenciador de secrets do ambiente de deploy.
- A senha deve ter no mínimo 12 caracteres e não pode usar valores fracos conhecidos.
- Faça rotação periódica das credenciais e sempre após incidentes.

## Política de dependências

- Use `uv.lock` como fonte única de versões aprovadas.
- Em CI/produção, execute instalação com lockfile:

```bash
uv sync --frozen
```

- Atualizações devem ser feitas por PR dedicado, com revisão e validação de testes.

## Rotina recomendada de atualização

1. Atualizar lockfile em branch específica.
2. Executar `python -m pytest`.
3. Executar varreduras de segurança (workflow `security`).
4. Revisar changelog das dependências críticas.
5. Aprovar e promover para produção.
