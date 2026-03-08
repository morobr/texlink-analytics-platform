# Business Glossary — Texlink Analytics

> Definitions of key business terms used across the Texlink analytics platform.

---

## Platform Entities

| Term | Portuguese | Definition |
|---|---|---|
| **Empresa** | Empresa | A brand, fashion label, or manufacturer that places production orders on the platform. Demand-side participant. |
| **Oficina** | Oficina de Costura | A sewing workshop or contract manufacturer (facção) that fulfills production orders. Supply-side participant. |
| **Pedido** | Pedido | A production order created by an empresa, specifying garment type, quantity, and deadline. |
| **Proposta** | Proposta | A bid submitted by an oficina in response to a pedido, including price and timeline. |
| **Facção** | Facção | Industry term for outsourced sewing/manufacturing. Oficinas are facções. |

## Order Lifecycle

| Status | Description |
|---|---|
| **Rascunho** | Draft — order created but not yet published to the marketplace. |
| **Publicado** | Published — order visible to oficinas, open for proposals. |
| **Em Negociação** | Negotiating — proposals received, empresa evaluating bids. |
| **Aceito** | Accepted — empresa selected a proposal, oficina confirmed. |
| **Em Produção** | In Production — oficina actively manufacturing the order. |
| **Finalizado** | Completed — production finished, delivery confirmed. |
| **Cancelado** | Cancelled — order cancelled at any stage. |

## Key Metrics

| Metric | Definition | Formula |
|---|---|---|
| **GMV** | Gross Merchandise Value — total value of all orders on the platform. | SUM(pedidos.valor_total) |
| **Take Rate** | Platform's commission percentage on each transaction. | SUM(taxa_plataforma) / SUM(valor_total) |
| **Liquidity** | % of published orders that receive at least 1 proposal. | Orders with proposals / Published orders |
| **Time-to-Match** | Average hours from order publication to proposal acceptance. | AVG(accepted_at - published_at) |
| **Match Rate** | % of orders successfully matched with an oficina. | Matched orders / Total published orders |
| **AOV** | Average Order Value. | SUM(valor_total) / COUNT(pedidos) |
| **CLV** | Customer Lifetime Value — predicted total revenue from an empresa. | BG/NBD + Gamma-Gamma model output |
| **Win Rate** | % of proposals that get accepted (oficina metric). | Accepted proposals / Total proposals sent |
| **Fill Rate** | % of an oficina's monthly capacity utilized by orders. | Pieces assigned / capacidade_mensal |
| **Quality Score** | Composite score (0-100) for oficina reliability and quality. | Weighted: ratings + on-time + certifications + defect rate |
| **Churn Risk** | Probability that an entity becomes inactive in next 30 days. | Based on recency, frequency, and engagement decay |

## Industry Context

| Term | Definition |
|---|---|
| **ABVTEX** | Associação Brasileira do Varejo Têxtil — responsible supply chain certification. The most important compliance standard in Brazilian textile manufacturing. |
| **NBCU** | NBCUniversal — licensed manufacturer certification for branded products. |
| **Disney** | Disney licensed manufacturer certification — highest prestige tier. |
| **Peça** | A single garment/piece — the base unit of production. |
| **Lote** | A batch or lot of pieces in a single production run. |
| **Prazo** | Delivery deadline/timeline for an order. |

## Segmentation

### Empresa Segments (by porte)
- **MEI** — Micro-entrepreneur (< R$81k/year)
- **Micro** — Micro-enterprise (< R$360k/year)
- **Pequena** — Small enterprise (< R$4.8M/year)
- **Média** — Medium enterprise (< R$300M/year)
- **Grande** — Large enterprise (> R$300M/year)

### Oficina Tiers (by quality score)
- **Ouro** (Gold) — Score 80-100, top-tier workshops
- **Prata** (Silver) — Score 60-79, reliable workshops
- **Bronze** — Score 40-59, developing workshops
- **Básico** (Basic) — Score 0-39, new or underperforming
