# Checklist operacional de segurança para deploy

- [ ] Secrets de produção configurados no ambiente (sem credenciais padrão/fracas).
- [ ] Rotação de credenciais executada conforme política interna.
- [ ] Limites de upload revisados (`MAX_UPLOAD_SIZE_BYTES` e limites de extração).
- [ ] Rate limit e lockout de autenticação habilitados por configuração padrão.
- [ ] Workflow de segurança em CI sem falhas.
- [ ] Testes automatizados (`python -m pytest`) aprovados.
- [ ] Logs/telemetria de login e erros de extração monitorados.
- [ ] Plano de resposta a incidentes atualizado com contatos e SLA.
- [ ] Validação pós-release concluída (upload, comparação e exportação XLSX/PDF).
