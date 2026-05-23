# Reavaliação de segurança pós-correções

## Reduções de risco confirmadas

1. **Upload e parsing**
   - Limite de tamanho de arquivo.
   - Validação de tipo real por assinatura.
   - Bloqueio de conteúdo binário suspeito em formatos textuais.
   - Tratamento explícito e sanitizado de erros de parsing.

2. **Resiliência contra DoS**
   - Timeout de extração.
   - Limites de páginas/caracteres (PDF).
   - Limites de linhas/colunas/células (planilha).
   - Limites de linhas/caracteres (texto).

3. **Exportação XLSX**
   - Sanitização anti-fórmula para conteúdo controlado por usuário/documento.

4. **Autenticação**
   - Rate limit por sessão/IP.
   - Atraso progressivo por tentativas falhas.
   - Bloqueio temporário após exceder limite.
   - Telemetria básica de tentativas em log.

5. **Governança operacional**
   - Documentação de secrets e política de dependências com lockfile.
   - Checklist de segurança para deploy.
   - Workflows de segurança em PR/CI.

## Pendências residuais por severidade

- **Média**: rate limit depende de memória do processo; em escala horizontal recomenda-se backend compartilhado (Redis) para contagem global.
- **Média**: timeout de extração limita o tempo de resposta da requisição, mas threads de parsing iniciadas podem continuar executando em background até concluírem.
- **Baixa**: chaves por IP via `X-Forwarded-For`/`X-Real-IP` só devem ser habilitadas com proxy reverso confiável; por padrão usa identificador de sessão.
- **Baixa**: validação de tipo para `.csv`/`.txt` usa heurística binária; pode exigir inspeção MIME avançada em cenários mais heterogêneos.
- **Baixa**: PDFs extremamente complexos ainda podem gerar custo computacional elevado, apesar dos limites atuais.
