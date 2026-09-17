# 02 — Infraestructura (Terraform, desde el día 1)

## Por qué Terraform desde el arranque
No es "hice el agente y después le agregué Terraform" — la infra se declara antes de que exista una sola tabla. Esto es lo que separa este repo de "otro chatbot de Pokémon".

## Estructura
```
terraform/
├── providers.tf      # provider databricks + azurerm (o el cloud que corresponda)
├── variables.tf
├── storage.tf         # ADLS Gen2 / S3 para Bronze/Silver/Gold
├── databricks.tf      # workspace, catalog, schema, volumes
├── jobs.tf             # jobs del pipeline Medallion (bronze_ingest, silver_transform, gold_aggregate, dq_check)
├── apps.tf             # Databricks App para el MCP server (custom app)
├── permissions.tf     # Unity Catalog grants, service principal del app
└── outputs.tf
```

## Constraint real: 10 días de workspace pago
El workspace de Azure/Databricks (Premium SKU) con crédito se vence pronto. Prioridad de `terraform apply`:
1. Storage + catalog/schema (Bronze/Silver/Gold) — primero, para no perder el dataset curado si el workspace muere.
2. Jobs del pipeline — corrida completa antes de que se acabe el crédito.
3. Databricks App (MCP server) — se puede rearmar después si hace falta, no es tan urgente como tener el dataset a salvo.

**Antes de que se corte el free tier: exportar/materializar el Gold final a algo que sobreviva** (blob storage con capa gratuita, o export a archivo) — así el frontend/agente no dependen de que el workspace siga vivo para siempre.

## Databricks Apps — sin Dockerfile
El MCP server se declara como Databricks App: solo necesita `app.py` (o el entrypoint que sea) + `requirements.txt` + `app.yaml` opcional con el comando de arranque y env vars. Databricks construye y corre todo internamente — no hay container que nosotros administremos.

## CI/CD (mismo patrón que `databricks-medallion-terraform`)
GitHub Actions: `terraform plan` en cada PR, `terraform apply` en push a `main`. Acá también practicamos el escenario "Claude Code en CI/CD" del examen si sumamos un job que le pida a Claude Code revisar el plan antes del apply.

## Secrets — no repetir el error del proyecto de turismo
- Nunca un `.tfplan` ni `.tfstate` commiteado — van al `.gitignore` desde el primer commit, no cuando ya se filtró algo.
- Token de Claude, key de pokemontcg.io → variables de entorno / Databricks Secrets, nunca en un `.tf` ni en `app.yaml` en texto plano.
- Pre-commit hook con `gitleaks` o `detect-secrets` como segunda red.
