# Cancã — Registro de encerramento técnico de Governança e CI/CD

Data de referência: 2026-11-02  
Escopo: governança do repositório, automação GitHub Actions, segurança de esteiras e processo de entrega. **Não** equivale à aprovação funcional da versão Alpha.

## Matriz de evidências

| Fase | Controle / evidência | Verificação | Estado |
| --- | --- | --- | --- |
| 1 — Segurança | Ruleset ativo: Protect default branch (id 24879062) | API: default branch, 8 checks obrigatórios, PR, histórico linear, bloqueio de exclusão e force push, CodeQL | Verificado |
| 1 — Segurança | CODEOWNERS, secret scanning, Dependabot e permissões de workflows | PRs #289 e #290; controles de arquivos presentes | Implementado; revisar periodicamente configurações e alertas |
| 2 — Qualidade | Python CI, CodeQL, Dependabot, Dependency Review, Ruff, pip-audit e Bandit | PRs #279–#291 e #311; 30/30 checks no merge #311 | Implementado; achados consultivos históricos ainda exigem triagem |
| 2 — Quality Gate | Bandit security baseline obrigatório | Ruleset exige check; #311 falha diante de erro de execução; gate incremental de HIGH em linhas adicionadas | Verificado no código e na integração; teste negativo isolado ainda não registrado |
| 3 — Governança | GitHub Projects V2, quatro views, Insights e auditoria GraphQL | PRs #292–#300, #301–#302; auditoria Projects V2 executada | Operacional; dados históricos incompletos |
| 3 — Evidências | Four-Phase Governance Evidence Audit #1 | Run 41509090609; quatro conjuntos de arquivos presentes | Executado com sucesso; não substitui aceite |
| 4 — Preflight | Release Preflight #2 | Run 41508156560: 29 checks aprovados, decisão review_required, nenhuma release publicada | Executado com sucesso |
| 4 — Reconstrução | Delivery Configuration Recovery Drill #1 | Run 41489214487 | Executado com sucesso — arquivos isolados |
| 4 — Reversão isolada | Git Revert Rehearsal #1 | Run 41508093858 | Executado com sucesso — repositório temporário |
| 4 — Reversão real por PR | PR #309 adicionou marcador; PR #310 removeu | Merges aprovados; commit final e819af649f9c; arquivo ausente na main | Concluído no escopo documental de teste |

## Riscos residuais e limites

1. **Bandit:** o gate incremental bloqueia HIGH em linhas novas detectadas. Não garante ausência de vulnerabilidades introduzidas fora dessas linhas, e os achados históricos MEDIUM/LOW permanecem sujeitos a triagem.
2. **Ruff e pip-audit:** alguns relatórios são consultivos; devem ser interpretados separadamente dos checks obrigatórios. Checks aprovados não significam automaticamente nenhuma pendência de segurança.
3. **Projetos:** cobertura incompleta dos campos Priority, Workstream e Target Release; os itens históricos devem ser classificados conforme evidências, sem inferências arbitrárias.
4. **Prontidão Alpha:** não validada. Homologações SQL, coletores, SSH/WinRM, EVE-NG e recuperação do *runtime* pertencem à etapa posterior do produto.
5. **Recuperação:** o ensaio de reversão por PR validou um arquivo documental inofensivo; não comprova recuperação de banco de dados ou ambiente de produção.
6. **Manutenção:** avisos de depreciação de versões Node usadas por actions e alteração futura do ubuntu-latest devem ser monitorados.

## Critérios de aceite e decisão

- **Fase 1:** controles principais confirmados pela API; revisão contínua dos alertas e credenciais permanece operacional.
- **Fase 2:** check Bandit obrigatório e fail-closed integrado; riscos residuais e limites do gate documentados.
- **Fase 3:** views e Insights operacionais, relatórios de auditoria executados; saneamento de campos históricos permanece backlog.
- **Fase 4:** preflight, reconstrução e dois ensaios de reversão demonstrados no escopo de governança e entrega.

**Proposta de decisão:** aprovar o encerramento das fases 1–4 **somente no escopo de governança e CI/CD**, com aceite explícito dos riscos residuais listados acima. A decisão final pertence ao responsável pelo projeto e deve ser registrada em PR/Issue de aceite ou documento equivalente; este texto não concede aceite automaticamente.

## Referências

- Ruleset: https://github.com/brunosfs-droid/canca/rules/24879062
- Segurança Bandit: https://github.com/brunosfs-droid/canca/pull/311
- Auditoria quatro fases: https://github.com/brunosfs-droid/canca/actions/runs/41509090609
- Preflight: https://github.com/brunosfs-droid/canca/actions/runs/41508156560
- Recuperação: https://github.com/brunosfs-droid/canca/actions/runs/41489214487
- Revert isolado: https://github.com/brunosfs-droid/canca/actions/runs/41508093858
- PRs de rollback: https://github.com/brunosfs-droid/canca/pull/309 e https://github.com/brunosfs-droid/canca/pull/310
