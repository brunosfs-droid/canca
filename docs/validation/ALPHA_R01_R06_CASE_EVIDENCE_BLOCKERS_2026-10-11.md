# Cancã — Alpha Marco B: matriz caso → suite → evidência → bloqueador (2026-10-11)

Base de integração: PR #217, squash `a0f72a5a5e7a17af51ae01ce646e51d440ba6347`. A matriz não declara homologação operacional e não substitui `E0_EVIDENCE_REGISTER_v0.6.81.md`.

| Requisito | Casos | Suites disponíveis | Evidência existente | Bloqueador para aceite |
| --- | --- | --- | --- | --- |
| R01 | T01/T02 | `test_postgres_workspace.py`, `test_workspace_service.py`, `test_workspace_api.py` | CI SQL/API com isolamento sintético | LAB A/B com IP/ID igual e contraprova store/cache/download/secrets |
| R02 | T03/T14 | `test_workspace_coordinator.py`, `test_workspace_legacy_jobs.py` | Subprocesso **real local** `P01_Discovery_Node.py status --json`; testes cancel/timeout/grupo de processos, **sem rede** | Adapters de scanner/collector reais ainda não passam integralmente por lease/generation/drain; I/O AUTH/FULL, multi-host, p50/p95/RAM e validação EVE |
| R03 | T04/T05 | `test_workspace_model.py`, `test_workspace_legacy.py` | Identidade, observation, replay e provenance | Categorias adicionais e backfill/idade com material real |
| R04 | T02/T06 | `test_workspace_model.py` | Grafo manual limitado/ownership | Interfaces, redes, VLANs e serviços observados por adapters; ciclos e ownership |
| R05 | T05/T07 | `test_workspace_model.py`, `test_workspace_api.py`, `test_workspace_legacy.py` | Preview/apply, revision fencing, receipt e rollback | Seleção multicategoria, drift, colisões, crash em commit |
| R06 | T01/T04/T13 | `test_workspace_recovery.py`, `test_workspace_backup_guard.py` | Recovery sintético/SQL e preflight offline | Restore independente cross-cluster de DB/store/roles/RLS/TLS, E0 e sign-off |

## R02 — próximo incremento funcional verificável

**G0 — contratos e limites, antes de rede:** identificar entrypoints reais de scanner e coletores WinRM/SSH/SNMP, seus subprocessos/threads, diretórios de output e consumidores SQL. A entrada deve ser **interna** e vinculada a `Operation` ativo; não criar endpoint que permita AUTH/FULL automaticamente.

**G1 — admissão:** autorização, escopo e workspace owner antes de credenciais ou I/O; token/lease/generation fixados; um job por operação; uso de raízes privadas verificadas; limites de runtime e memória.

**G2 — interrupção durante I/O:** `Operation.check()` antes e depois de cada fronteira I/O, cancelamento propagado, subprocessos e descendentes terminados/verificados; em limpeza inconclusiva `fail_closed()`. Proibir novo workspace até confirmação de drain.

**G3 — persistência:** sem output publicado/cache compartilhado/cursor/revision SQL após cancelamento ou troca de geração. Commit requer fencing atômico transacional além de check em Python.

**G4 — regressão reproduzível:** cenários A→B com o mesmo IP, cancelamento em handshake/exec/timeout/close, credenciais indisponíveis, subprocesso órfão, I/O travado e falha de rollback. Validar Windows e POSIX separadamente; registrar run/job SHA, duração, p50/p95/RAM em datasets dimensionados.

**G5 — operacional E0:** operador do LAB autoriza escopos privados, configura credenciais fora do Git, executa E0-02, E0-03, E0-05 e E0-06 e arquiva evidência privada com digest; E0 permanece NOT RUN até então.

## Exclusões explícitas

Nenhum scanner autenticado, operação de rede ou restore foi executado nesta atualização documental. Checkpoint `status --json` não prova comportamento de scans reais. A UI Mapper continua na fase v0.7. Não usar mais versões v0.6.xx para expandir apenas casos periféricos sem atacar G1–G4.

## Decisão de gate

**R02: BLOCKED (integração AUTH/FULL e E0)**. **Alpha: NO-GO** até fechamento R01–R06 e evidência operacional. Código e testes devem entrar por PRs separadas, com CI e revisão de segurança.
