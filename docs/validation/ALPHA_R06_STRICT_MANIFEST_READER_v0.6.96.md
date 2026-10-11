# Cancã v0.6.96 — leitura estrita e protegida do manifesto R06

## Problema

Os artefatos de backup são protegidos contra alterações de caminho e links simbólicos no POSIX (v0.6.94–95). Entretanto, a etapa de **verificação do manifesto** ainda carregava JSON usando leitura por nome de arquivo. Ela podia aceitar chaves repetidas (última definição vence), constantes não padronizadas como \`NaN\` e registros semanticamente imprecisos. Um link simbólico poderia ser introduzido entre inspeção e abertura do próprio manifesto.

## Contrato implementado

- \`_manifest_read()\` valida arquivo regular não vazio, tamanho de no máximo **16 KiB**, abertura com descritores e \`O_NOFOLLOW\` no POSIX, e identidade do inode/metadados antes, durante e após a leitura. Entrada que não puder ser confirmada falha com \`manifest_invalid\`, sem imprimir dados privados.
- \`_strict_manifest()\` aceita somente JSON UTF-8 conforme o contrato canônico \`canca-alpha-e0-artifacts-v1\`. Rejeita chaves duplicadas em qualquer nível, \`NaN\`/\`Infinity\`/\`-Infinity\`, campos extras, faltantes e estruturas inesperadas.
- Exige os quatro artefatos \`database_dump\`, \`roles_snapshot\`, \`store\` e \`configuration\`. Os arquivos individuais exigem \`sha256\` e \`bytes\`. As árvores exigem \`sha256\`, \`bytes\`, \`files\` e \`directories\`.
- Digest é exatamente 64 caracteres hexadecimais minúsculos; contagens/tamanhos devem ser **inteiros reais**, nunca booleanos ou floats. Os arquivos/árvores não podem ser vazios e os totais respeitam \`MAX_ENTRIES\`.
- O procedimento continua comparando o conteúdo completo do manifesto com hashes calculados novamente a partir das origens. Um manifesto válido porém diferente dos artefatos continua produzindo \`artifact_mismatch\`, enquanto conteúdo estruturalmente inválido produz \`manifest_invalid\`.

## Testes

\`\`\`bash
python -m unittest discover -s tests -p 'test_alpha_e0_recovery_preflight.py' -v
\`\`\`

A suíte de regressão inclui chaves JSON duplicadas na raiz e em artefatos, valores numéricos inválidos, extras/omissões, tamanho acima do limite, symlink no manifesto e em diretório ancestral, além de substituição controlada entre \`lstat\` e \`open\`. A captura/verificação normal e os manifestos canônicos v1 seguem compatíveis.

## Limites e homologação

Em Windows e plataformas sem \`O_NOFOLLOW\`/dir_fd, continuam aplicáveis as verificações de identidade pré/pós-leitura, **sem garantia equivalente de proteção contra troca de symlink antes da abertura**. O SHA-256 compara conteúdo com o manifesto recebido; não prova autenticidade do remetente, assinatura independente, execução de backup coerente, roles/grants/RLS/TLS, integridade transacional nem restore entre clusters.

A Alpha permanece **NO-GO**: E0-01..E0-10 continuam \`NOT RUN\`; R06 cross-cluster, R02/T14 e homologação no EVE-NG requerem intervenção operacional autorizada. Nenhum restore ou teste destrutivo é executado por esta entrega.
