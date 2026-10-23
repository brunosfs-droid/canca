# R03 — Interface SQL writer: gate de aceitação E0

Status: **NÃO HOMOLOGADO**. Documento de execução, não declaração de conformidade.

## Escopo
Writer `persistence/P01_Interface_SQL_Writer.py`, migração opt-in 0011, `P01_Workspace_Model.scope`, lease de `P01_Workspace_Coordinator`, RLS e segregação de papéis PostgreSQL. A observação é histórica e não comprova identidade física de porta ou topologia.

## Qualificação reproduzível de CI
- Os jobs `PostgreSQL CI / metadata-transactions (16,17)` executam `CANCA_TEST_WORKSPACE_POSTGRES=1 python -m unittest discover -s tests -p "test_interface*postgres.py" -v`.
- Os jobs `Workspace Foundation CI / workspace-isolation (16,17)` também devem passar.
- Python CI, CodeQL, Operator Web/Accounts, SNMP read-only e Optional Agent devem passar no **mesmo SHA do PR**.
- Falha no passo *Initialize containers* significa **não executado**, nunca teste aprovado. Reexecutar apenas o job afetado, registrar run, SHA, versão PostgreSQL, conclusão e evidência de execução dos testes. Se persistir, investigar runner/imagem antes de aprovar.
- Não usar aprovação de um SHA anterior para liberar um commit novo.

## Controles automatizados esperados
1. Migração 0011 integral e hash/versão válidos; nenhuma migração implícita no fluxo normal.
2. Escrita positiva com papel `workspace:write`, lease PostgreSQL real e token da geração atual.
3. Idempotência: replay do mesmo lote insere zero; alteração de dados preexistentes falha sem mutação.
4. Histórico: novo `collection_id` preserva coleta anterior; chaves incluem `workspace_id`.
5. RLS: negar papel sem grant, papel read-only, grant de outro workspace e acesso após revogação.
6. Fencing: negar token após `SessionLease.stop`, após recuperação e após troca de workspace.
7. Atomicidade: rollback total por conflito, erro SQL, falha de restrição ou revogação antes do commit; conexão reutilizável após erro.
8. Associação das evidências por caminho + SHA-256 verificado; rejeição de ownership ambíguo e duplicação de observation IDs.

## Homologação operacional E0 — exige operador
- [ ] Preparar banco PostgreSQL de laboratório **descartável**, sem dados corporativos nem credenciais reais em logs; confirmar backup e restore conforme roteiro de recuperação existente.
- [ ] Aplicar migrações até 0011 explicitamente e registrar checksums/versão do schema.
- [ ] Provisionar separadamente papel coordenador e escritor mínimo; inspecionar grants/RLS com papel não privilegiado.
- [ ] Importar bundle assinado/verificado do laboratório EVE-NG; registrar caminhos e SHA-256 (sem segredos).
- [ ] Importar a coleta duas vezes, conferir contagem 1ª inserção versus replay e consultar histórico por workspace.
- [ ] Revogar grant com lease ainda ativo; verificar negação, ausência de inserções parciais e preservação do histórico.
- [ ] Encerrar/reabrir coordenador e alternar workspaces; comprovar negação com tokens obsoletos e sucesso com token novo.
- [ ] Simular interrupção/rollback; repetir a coleta e verificar recuperação consistente e integridade do restore.
- [ ] Registrar resultados, SHA, logs higienizados, operador e data; documentar desvios e decisão final.

## Decisão de release
**Bloquear merge** enquanto qualquer job estiver falho, em execução ou não executado, ou enquanto a evidência operacional E0 não estiver registrada e revisada. A suíte CI usa evidências de inventário simuladas em pontos controlados; não comprova sozinha importação EVE-NG real nem restauração operacional.

## Matriz de evidências automatizadas (referência de testes)

| Critério | Evidência no repositório |
| --- | --- |
| Lease ativo e escrita real; replay | `test_live_lease_authorizes_actual_writer_and_idempotent_replay` |
| Fence no commit, rollback e retry | Mesmo teste, lote `batch-fenced` |
| Encerramento e recuperação do lease | Mesmo teste, lotes `batch-after-stop` e `batch-stale-generation` |
| Troca de workspace | Mesmo teste, lote `batch-after-switch` |
| Revogação/restauração de permissão | `test_revoked_write_grant_blocks_real_writer_with_active_lease` |
| Grant read-only e grant em outro workspace | `test_read_only_workspace_grant_cannot_persist_interfaces` e `test_writer_grant_in_other_workspace_cannot_write_target` |
| Append-only e RLS obrigatório | `test_interface_writer_role_cannot_update_or_delete_history` e `test_interface_history_table_enforces_rls_and_has_no_mutation_policies` |
| Chave primária e histórico temporal | `test_interface_history_primary_key_scopes_batch_and_observation` e `test_idempotent_replay_preserves_original_observed_at` |
| Falha e recuperação SQL | `test_sql_constraint_abort_leaves_connection_reusable_for_next_batch` |

**Critério de aprovação:** consultar cada nome no log do `PostgreSQL CI` na versão 16 e 17. O nome no código não representa aprovação até que a execução no SHA de release seja confirmada. A etapa E0 com evidência real permanece separada.

## Evidência CI consolidada — candidato 973e32a (não é homologação E0)

- Commit validado: `973e32a2c74a28e12505e67fb67c0706d7d9b03f`.
- PostgreSQL CI: **success**, run `39667054149`, matrizes 16 e 17.
- Workspace Foundation CI: **success**, run `39667054777`, matrizes 16 e 17.
- Python CI: `39667054551` (success); CodeQL: `39667054449` (success).
- Operator Web CI: `39667054528` (success); Operator Accounts CI: `39667054296` (success).
- Read-only SNMP CI: `39667054132` (success); Optional Agent CI: `39667054278` (success).
- Dependência de contêiner corrigida nos dois workflows: `public.ecr.aws/docker/library/postgres` substituída por `postgres`; falhas anteriores de *Initialize containers* decorriam de `toomanyrequests: Data limit exceeded` no ECR Public.
- Estes resultados são vinculados ao SHA acima. **Se houver novo commit, a matriz inteira precisa ser reconfirmada no novo SHA.**
- Permanecem pendentes: execução E0 com bundle do EVE-NG, evidência de restauração operacional, registro de aprovação e decisão de liberação.

## Registro mais recente de CI — 6cd1f68

SHA: `6cd1f68f9b50c506ee8916e7d3903da4c23dd7f0`. Oito workflows **success**:
- PostgreSQL CI `39669735010`
- Workspace Foundation CI `39669735361`
- Python CI `39669735018`
- CodeQL `39669735547`
- Operator Web CI `39669735069`
- Operator Accounts CI `39669735035`
- Read-only SNMP CI `39669734875`
- Optional Agent CI `39669735070`

### Modelo de evidência da sessão E0

Preencher durante a execução, sem publicar segredos ou dados identificáveis:

| Campo | Valor |
| --- | --- |
| Commit/branch validado | PENDENTE |
| Data UTC e operador | PENDENTE |
| Versão PostgreSQL e schema/checagem | PENDENTE |
| Ambiente e origem do bundle verificado (IDs não sensíveis) | PENDENTE |
| SHA-256 do bundle e quantidade de interfaces | PENDENTE |
| Escrita inicial / replay / segunda coleta | PENDENTE |
| Revogação de grant e isolamento de workspace | PENDENTE |
| Encerramento/troca de lease e tokens obsoletos | PENDENTE |
| Falha transacional, retry, backup e restore | PENDENTE |
| Evidências/logs higienizados | PENDENTE |
| Desvios, responsável pela correção, decisão | PENDENTE |

**Não interpretar este modelo como execução realizada.** As evidências operacionais continuam pendentes.

## Pré-validação automatizada E0 em banco descartável

O repositório fornece `docs/validation/R03_E0_PREFLIGHT.sh` para executar os testes de integração R03 com PostgreSQL local, sem imprimir credenciais, nomes do banco ou dados corporativos:

```bash
# Somente no clone do repositório e com PostgreSQL LAB isolado,
# usando as variáveis PGHOST, PGDATABASE e PGUSER já configuradas.
CANCA_E0_EXPECTED_DB="$PGDATABASE" CANCA_E0_DISPOSABLE_DB=YES \
  bash docs/validation/R03_E0_PREFLIGHT.sh
```

**AVISO: A suíte remove e recria o schema `canca`.** O runner bloqueia a execução sem confirmação explícita `CANCA_E0_DISPOSABLE_DB=YES`; jamais utilizar em banco compartilhado, staging ou produção. Essa pré-validação não substitui testes com bundle verificado do EVE-NG nem backup/restore E0.

## Execução do preflight com artefatos — SHA 2509981

- Commit: `25099817905d2e2e0da281db6ae48e6d4e182998`.
- PostgreSQL CI run: `39883743859`, conclusão **success**.
- PostgreSQL 16: job `metadata-transactions (16)`, preflight, geração/upload de evidência e smoke backup/restore **success**; artefato `r03-preflight-postgres-16` (ID `12471841606`).
- PostgreSQL 17: job `metadata-transactions (17)`, preflight, geração/upload de evidência e smoke backup/restore **success**; artefato `r03-preflight-postgres-17` (ID `12471662189`).
- Ambos os artefatos estavam disponíveis e não expirados no momento da consulta; retenção configurada em 14 dias.
- **Escopo:** banco descartável de CI. Estes arquivos não demonstram execução operacional E0 com bundle EVE-NG nem recuperação e restore no ambiente alvo. A aprovação requer evidências operacionais separadas.

## Gate automatizado validado — SHA 1bd9c2c

- Commit: `1bd9c2c0735ac8f27877026accdc6f0c8c76e2e5`.
- Oito workflows `success`, incluindo PostgreSQL CI run `39887502675`.
- PostgreSQL 16: job `metadata-transactions (16)` success; artefato `r03-preflight-postgres-16`, ID `12473217788`.
- PostgreSQL 17: job `metadata-transactions (17)` success; artefato `r03-preflight-postgres-17`, ID `12472814101`.
- Nos dois jobs, a sequência `preflight → backup/restore → geração/upload de evidência` consta como **success**.
- Artefatos confirmados não expirados na consulta, com retenção de 14 dias.
- **Ainda não representa E0 aprovado:** bundle EVE-NG real, execução no ambiente alvo, recuperação operacional e aprovação final continuam pendentes.
