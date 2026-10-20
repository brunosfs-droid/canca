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
