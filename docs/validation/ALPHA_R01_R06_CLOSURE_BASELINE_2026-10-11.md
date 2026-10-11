# Cancã — Marco B: rastreabilidade e fechamento R01–R06

Baseline de auditoria: 2026-10-11. PR #208 integrada por squash em `7abf890c0d01cde533368767f98c56653aed91cd`. Os oito workflows do HEAD pré-merge `d8a3313e1a208150a8e07565e5e6a2a9925dfbfc` foram SUCCESS. **Não equivalem a aceite operacional**.

Fonte normativa: `docs/BACKLOG_1.0.md`, `docs/TEST_PLAN_1.0.md`, `docs/validation/ALPHA_R01_R06_GATE_MATRIX_2026-10-08.md`, `docs/validation/E0_OPERATIONAL_ACCEPTANCE_v0.6.80.md` e `docs/LAB_ALPHA_E0_AND_RECOVERY_R1.md`.

## Matriz de fechamento

| Gate | Implementação e suites disponíveis | Lacuna de evidência e implementação | Critério de fechamento |
| --- | --- | --- | --- |
| R01 / T01,T02 | Registry, sites, environments, grants/RLS; test_postgres_workspace.py, test_workspace_model.py, test_workspace_api.py | Auditoria de ownership/backfill, readers, store, cursors, downloads, caches e secrets; execução LAB A/B | Nenhum vazamento ou concessão implícita com identidades/IPs coincidentes, SQL/API/store testados |
| R02 / T03,T14 | Lease/generation/drain, cancelamento e quarentena, regressões sintéticas v0.6.89–93 | Adapters de scanners/collectors reais, concorrência sob I/O, multi-host e p50/p95/RAM de carga representativa | Nenhum job/commit tardio, crossover A/B ou token antigo aceito após drain, medições registradas |
| R03 / T04,T05 | CollectionRun/Observation, identity/replay, readers de sinais/proveniência; test_workspace_model.py, test_workspace_legacy.py | Categorias além de identity, migração completa, proveniência e idade em material real | Bytes/IDs/hashes/revisões preservados sem merge implícito; imports repetidos idempotentes |
| R04 / T02,T06 | Objetos/relações manuais, grafo limitado e ownership | Interfaces, redes/VLAN, componentes e serviços observados por adapters; contraprovas de ciclos e escopo | Grafo backend qualificado, declared/observed separados; **UI Mapper é v0.7** |
| R05 / T05,T07 | Preview/apply, revision fence, receipts/rollback, legado revisado | Importação seletiva multi-categoria, dry-run com drift, colisões e interrupção de commit | Apply atômico, sem overwrite/deletion implícitos, conflito explícito, replay consistente |
| R06 / T01,T04,T13 | API autenticada, auditoria HTTP, recuperação sintética schema8/9, preflight de manifesto reforçado até v0.6.96 | Restore real entre clusters com roles/grants/RLS/TLS/config/store, migração integral e revalidação A/B | Recovery independente qualificado, rollback seguro, R01–R05 fechados e sign-off |

## Gates E0 operacionais

O registro `docs/validation/E0_EVIDENCE_REGISTER_v0.6.81.md` indica **E0-01..E0-10 = NOT RUN**; não alterar para PASS sem resultado real. Executar na ordem e com evidências: package/import; WinRM autorizado; SSH autorizado; endpoint negado; isolamento A/B; coordinator/drain; import/reconciliation; same-cluster recovery; audit/redaction; rollback/repeatability.

**Preflight obrigatório:** commit SHA e 8 checks, export da topologia EVE-NG e SHA-256, operadores e escopo, relógio/DNS/rotas, snapshots e rollback, credenciais em provedor privado. Sem autorização específica, não executar scanner, AUTH/FULL, restore, grants, SQL destrutivo ou exploração fora da rede LAB autorizada.

**Restore cross-cluster:** hold point independente, cluster de destino descartável diferente da origem, checagem de versões/extensões/roles/TLS, captura coerente DB/store/config e prova SHA, restauração e validação de dados, RLS, leases, reabertura e RTO/RPO. Não executar restore no cluster original.

## Próxima fila de execução (bloqueadores primeiro)

1. Revisar implementações R01–R06 contra contratos T01–T07/T13; criar matriz caso→suite→evidência com SHA, status e lacuna; classificar `BLOCKER` ou `POST-ALPHA`.
2. Priorizar adapters R02 com I/O real; completar fluxos exigidos de R03–R05; nenhum novo `v0.6.xx` somente por expansão de testes.
3. Preparar execução E0 com operador; registrar PASS/FAIL/BLOCKED/NOT RUN e digest privado.
4. Qualificar cross-cluster R06 e corrigir somente bloqueadores, cada alteração mediante PR e CI completo.
5. Gate de release: zero bloqueadores P0 sem aceite, E0 aprovado, documentação e decisão explícita GO/NO-GO. Recursos R07/R08 de UI/Mapper da v0.7 não se presumem completos aqui.

## Segurança do repositório público

PR #207 (`security/public-repository-hygiene`) foi integrada à `main` em 2026-10-11 pelo squash commit `efe7bdad517c2819ee28d72a2592baba87df2166` com 22 checks aprovados. A sanitização do HEAD não remove, por si só, dados históricos do Git: avaliar eventuais segredos expostos e rotação/limpeza de histórico em procedimento separado. Alertas de CodeQL devem ser tratados em hardening específico, sem confundi-los com o fechamento R01–R06.

## Estado da auditoria

Marco B: **rastreabilidade inicial consolidada; implementação e homologação ainda abertas**. Nenhum EVE-NG executado, nenhum restore real, nenhuma evidência inventada.