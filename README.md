# Micael Monitor Phoenix

Plataforma multiplataforma de monitoramento e inteligência situacional da família Micael, desenvolvida pela HYBRID Tecnologia Inteligente.

## Estado

**Developer Preview em desenvolvimento.**

O repositório contém a fundação técnica do backend e ainda não representa uma versão operacional do produto para usuários finais.

## Fundação implementada na linha de desenvolvimento

- API FastAPI versionada;
- configuração e logging estruturado;
- contexto de requisição e Request ID;
- envelope padronizado de respostas e erros;
- SQLAlchemy assíncrono e PostgreSQL;
- Alembic e migration inicial de Identity;
- modelos `User`, `Role`, `Permission` e `AuditLog`;
- testes iniciais da API;
- pipeline de qualidade do backend.

## Próximos marcos

1. Validar a migration de Identity em PostgreSQL.
2. Implementar autenticação e autorização RBAC funcionais.
3. Concluir auditoria automática.
4. Iniciar Organizations, Locations e Assets.
5. Evoluir para Discovery, Streaming, Recording, Events e IA.

## Núcleo de produto

- Atlas Runtime
- Vision Engine
- Sentinel
- Genesis
- Diagnostics

## Plataformas previstas

- Windows 11
- Linux Mint / Ubuntu
- Appliance

## Princípios

- Evidence First
- Zero Lost Events
- Fail Isolated
- Observable by Design
- API First

## Separação de produtos

O **Micael Monitor** pertence à família Micael. O **HYBRID Condo**, o **HYBRID Home Assistant** e o **Hercules** são produtos independentes e não fazem parte deste repositório.
