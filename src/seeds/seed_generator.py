"""
Texlink Analytics — Seed Data Generator
========================================
Generates realistic Brazilian textile marketplace data using Faker.
Produces all entities respecting referential integrity and business logic.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import yaml
from faker import Faker
from loguru import logger

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

fake = Faker("pt_BR")
fake_en = Faker("en_US")
random.seed(42)
Faker.seed(42)

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def _dt(d: datetime) -> datetime:
    """Ensure datetime is timezone-aware."""
    if d.tzinfo is None:
        return d.replace(tzinfo=UTC)
    return d


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(path: str = "src/seeds/seed_config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# CNPJ generator (valid format, not validated)
# ---------------------------------------------------------------------------

def _cnpj() -> str:
    """Generate a random CNPJ-formatted string (14 digits with formatting)."""
    nums = [random.randint(0, 9) for _ in range(12)]
    return (
        f"{nums[0]}{nums[1]}.{nums[2]}{nums[3]}{nums[4]}.{nums[5]}{nums[6]}{nums[7]}"
        f"/{nums[8]}{nums[9]}{nums[10]}{nums[11]}-{random.randint(10, 99)}"
    )


# ---------------------------------------------------------------------------
# Brazilian company name parts
# ---------------------------------------------------------------------------

_SUFIXOS = ["Confecções", "Têxtil", "Modas", "Indústria Têxtil", "Facção", "Costura",
            "Produções", "Vestuário", "Moda"]
_RAZAO_SUFIXOS = ["LTDA", "S.A.", "EIRELI", "ME", "EPP", "S/A"]


def _empresa_name() -> tuple[str, str]:
    """Returns (razao_social, nome_fantasia)."""
    base = fake.last_name()
    fantasia = f"{base} {random.choice(_SUFIXOS)}"
    razao = f"{fantasia} {random.choice(_RAZAO_SUFIXOS)}"
    return razao, fantasia


def _oficina_name() -> tuple[str, str]:
    last = fake.last_name()
    fantasia = f"Oficina {last} {random.choice(['Costura', 'Facção', 'Confecção', 'Têxtil'])}"
    razao = f"{fantasia} {random.choice(_RAZAO_SUFIXOS)}"
    return razao, fantasia


# ---------------------------------------------------------------------------
# Weighted random choice helper
# ---------------------------------------------------------------------------

def _weighted_choice(items: list[str], weights: list[float]) -> str:
    return random.choices(items, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Date/time helpers
# ---------------------------------------------------------------------------

def _random_dt(start: datetime, end: datetime) -> datetime:
    delta = end - start
    total = int(delta.total_seconds())
    if total <= 0:
        return _dt(end)
    secs = random.randint(0, total)
    return _dt(start + timedelta(seconds=secs))


def _business_hours_dt(base: datetime) -> datetime:
    """Shift a datetime to business hours (8–18h Mon–Fri, Brazilian)."""
    # Add up to 8 hours of business offset
    offset_hours = random.uniform(0, 8)
    candidate = base.replace(hour=8, minute=0, second=0) + timedelta(hours=offset_hours)
    # Skip weekends
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return _dt(candidate)


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------

@dataclass
class TexlinkDataset:
    """Container for all generated seed data."""
    categorias: list[dict] = field(default_factory=list)
    empresas: list[dict] = field(default_factory=list)
    oficinas: list[dict] = field(default_factory=list)
    usuarios: list[dict] = field(default_factory=list)
    pedidos: list[dict] = field(default_factory=list)
    pedido_items: list[dict] = field(default_factory=list)
    propostas: list[dict] = field(default_factory=list)
    producao: list[dict] = field(default_factory=list)
    avaliacoes: list[dict] = field(default_factory=list)
    certificacoes: list[dict] = field(default_factory=list)
    pagamentos: list[dict] = field(default_factory=list)
    mensagens: list[dict] = field(default_factory=list)
    eventos_plataforma: list[dict] = field(default_factory=list)
    notificacoes: list[dict] = field(default_factory=list)


class TexlinkSeeder:
    def __init__(self, config: dict):
        self.cfg = config
        self.ds = TexlinkDataset()
        self.start_dt = _dt(datetime.fromisoformat(config["start_date"]))
        self.end_dt = _dt(datetime.now(UTC) - timedelta(days=1))
        self._used_emails: set[str] = set()

        # Lookup maps built as we go
        self._empresa_ids: list[str] = []
        self._oficina_ids: list[str] = []
        self._usuario_ids: list[str] = []
        self._empresa_usuario_map: dict[str, list[str]] = {}  # empresa_id -> [usuario_id]
        self._oficina_usuario_map: dict[str, list[str]] = {}  # oficina_id -> [usuario_id]
        self._categoria_ids: list[str] = []
        self._admin_usuario_id: str = ""

    def _unique_email(self) -> str:
        """Generate a guaranteed-unique email address."""
        for _ in range(100):
            email = fake.email()
            if email not in self._used_emails:
                self._used_emails.add(email)
                return email
        # fallback: uuid-based
        email = f"user_{uuid.uuid4().hex[:8]}@texlink.com.br"
        self._used_emails.add(email)
        return email

    # -----------------------------------------------------------------------
    # 1. Categorias
    # -----------------------------------------------------------------------

    def gen_categorias(self) -> None:
        logger.info("Generating categorias_produto...")
        cat_cfg = self.cfg["categorias_produto"]
        for parent_def in cat_cfg:
            parent_id = str(uuid.uuid4())
            self.ds.categorias.append({
                "id": parent_id,
                "nome": parent_def["nome"],
                "slug": parent_def["nome"].lower().replace(" ", "-"),
                "descricao": f"Categoria principal: {parent_def['nome']}",
                "parent_id": None,
                "nivel": 1,
                "ativo": True,
                "created_at": self.start_dt,
                "updated_at": self.start_dt,
            })
            self._categoria_ids.append(parent_id)

            for sub in parent_def.get("subcategorias", []):
                sub_id = str(uuid.uuid4())
                self.ds.categorias.append({
                    "id": sub_id,
                    "nome": sub,
                    "slug": sub.lower().replace(" ", "-").replace("/", "-"),
                    "descricao": f"Subcategoria de {parent_def['nome']}",
                    "parent_id": parent_id,
                    "nivel": 2,
                    "ativo": True,
                    "created_at": self.start_dt,
                    "updated_at": self.start_dt,
                })
                self._categoria_ids.append(sub_id)
        logger.info(f"  → {len(self.ds.categorias)} categorias")

    # -----------------------------------------------------------------------
    # 2. Empresas
    # -----------------------------------------------------------------------

    def gen_empresas(self) -> None:
        logger.info("Generating empresas...")
        n = self.cfg["empresas"]
        estados = list(self.cfg["estados"].keys())
        pesos_estados = list(self.cfg["estados"].values())
        segmentos = self.cfg["segmentos_empresa"]
        seg_nomes = [s["nome"] for s in segmentos]
        seg_pesos = [s["weight"] for s in segmentos]

        portes = ["micro", "pequena", "media", "grande"]
        porte_pesos = [0.45, 0.35, 0.15, 0.05]

        for i in range(n):
            estado = _weighted_choice(estados, pesos_estados)
            cidades = self.cfg["cidades_por_estado"][estado]
            cidade = random.choice(cidades)
            razao, fantasia = _empresa_name()
            eid = str(uuid.uuid4())
            # Spread creation over history with growth curve
            created_at = _random_dt(self.start_dt, self.end_dt)
            verificado = random.random() < 0.70
            volume_mensal = random.randint(200, 15000)

            self.ds.empresas.append({
                "id": eid,
                "razao_social": razao,
                "nome_fantasia": fantasia,
                "cnpj": _cnpj(),
                "email": f"contato@{fantasia.lower().replace(' ', '')[:15]}{i}.com.br",
                "telefone": fake.phone_number(),
                "website": f"https://www.{fantasia.lower().replace(' ', '')[:12]}.com.br",
                "logo_url": None,
                "endereco": fake.street_address(),
                "cidade": cidade,
                "estado": estado,
                "cep": fake.postcode(),
                "porte": _weighted_choice(portes, porte_pesos),
                "segmento": _weighted_choice(seg_nomes, seg_pesos),
                "volume_mensal": volume_mensal,
                "descricao": fake.text(max_nb_chars=200),
                "ativo": random.random() < 0.92,
                "verificado": verificado,
                "data_verificacao": _random_dt(created_at, self.end_dt) if verificado else None,
                "created_at": created_at,
                "updated_at": created_at,
                "deleted_at": None,
            })
            self._empresa_ids.append(eid)
        logger.info(f"  → {len(self.ds.empresas)} empresas")

    # -----------------------------------------------------------------------
    # 3. Oficinas
    # -----------------------------------------------------------------------

    def gen_oficinas(self) -> None:
        logger.info("Generating oficinas...")
        n = self.cfg["oficinas"]
        estados = list(self.cfg["estados"].keys())
        pesos_estados = list(self.cfg["estados"].values())
        tier_cfg = self.cfg["oficina_tiers"]
        tiers = list(tier_cfg.keys())
        tier_pesos = [tier_cfg[t]["weight"] for t in tiers]

        especialidades_pool = [
            "Camisetas", "Vestidos", "Calças Jeans", "Pijamas", "Uniformes",
            "Moda Praia", "Roupas Esportivas", "Lingerie", "Blazers",
            "Jaquetas", "Moda Infantil", "Shorts", "Bordados", "Sublimação",
        ]
        maquinario_pool = [
            "Máquina Reta", "Overlock", "Galoneira", "Interloque", "Travete",
            "Bordadeira", "Máq. de Botão", "Prensa Sublimação", "Corte Automático",
        ]

        for i in range(n):
            estado = _weighted_choice(estados, pesos_estados)
            cidades = self.cfg["cidades_por_estado"][estado]
            cidade = random.choice(cidades)
            razao, fantasia = _oficina_name()
            oid = str(uuid.uuid4())
            tier = _weighted_choice(tiers, tier_pesos)
            t_cfg = tier_cfg[tier]
            score_q = round(random.uniform(*t_cfg["score_range"]), 2)
            score_p = round(random.uniform(*t_cfg["score_range"]), 2)
            score_c = round(random.uniform(*t_cfg["score_range"]), 2)
            num_costureiras = random.randint(5, 80)
            cap_min, cap_max = t_cfg["capacidade"]
            created_at = _random_dt(self.start_dt, self.end_dt)
            verificado = random.random() < 0.65

            n_especialidades = random.randint(2, 5)
            n_maquinario = random.randint(3, 8)

            self.ds.oficinas.append({
                "id": oid,
                "razao_social": razao,
                "nome_fantasia": fantasia,
                "cnpj": _cnpj(),
                "email": f"contato@{fantasia.lower().replace(' ', '')[:15]}{i}.com.br",
                "telefone": fake.phone_number(),
                "responsavel": fake.name(),
                "logo_url": None,
                "endereco": fake.street_address(),
                "cidade": cidade,
                "estado": estado,
                "cep": fake.postcode(),
                "num_costureiras": num_costureiras,
                "capacidade_mensal": random.randint(cap_min, cap_max),
                "especialidades": random.sample(especialidades_pool, n_especialidades),
                "maquinario": random.sample(maquinario_pool, n_maquinario),
                "tier": tier,
                "score_qualidade": score_q,
                "score_pontualidade": score_p,
                "score_comunicacao": score_c,
                "total_avaliacoes": random.randint(0, 50),
                "ativo": random.random() < 0.88,
                "verificado": verificado,
                "data_verificacao": _random_dt(created_at, self.end_dt) if verificado else None,
                "created_at": created_at,
                "updated_at": created_at,
                "deleted_at": None,
            })
            self._oficina_ids.append(oid)
        logger.info(f"  → {len(self.ds.oficinas)} oficinas")

    # -----------------------------------------------------------------------
    # 4. Usuarios
    # -----------------------------------------------------------------------

    def gen_usuarios(self) -> None:
        logger.info("Generating usuarios...")
        min_u, max_u = self.cfg["usuarios_per_empresa"]
        min_o, max_o = self.cfg["usuarios_per_oficina"]

        # Admin user
        admin_id = str(uuid.uuid4())
        self._admin_usuario_id = admin_id
        self.ds.usuarios.append({
            "id": admin_id,
            "email": "admin@texlink.com.br",
            "nome": "Admin Texlink",
            "telefone": "11999999999",
            "role": "admin",
            "avatar_url": None,
            "empresa_id": None,
            "oficina_id": None,
            "ultimo_login": _now(),
            "login_count": random.randint(100, 500),
            "ativo": True,
            "created_at": self.start_dt,
            "updated_at": self.start_dt,
            "deleted_at": None,
        })
        self._usuario_ids.append(admin_id)

        # Empresa users
        for eid in self._empresa_ids:
            empresa = next(e for e in self.ds.empresas if e["id"] == eid)
            n = random.randint(min_u, max_u)
            uids = []
            for j in range(n):
                uid = str(uuid.uuid4())
                role = "empresa_owner" if j == 0 else "empresa_user"
                created_at = empresa["created_at"]
                ultimo_login = _random_dt(
                    created_at + timedelta(days=1), self.end_dt
                ) if empresa["ativo"] else None
                self.ds.usuarios.append({
                    "id": uid,
                    "email": self._unique_email(),
                    "nome": fake.name(),
                    "telefone": fake.phone_number(),
                    "role": role,
                    "avatar_url": None,
                    "empresa_id": eid,
                    "oficina_id": None,
                    "ultimo_login": ultimo_login,
                    "login_count": random.randint(1, 200),
                    "ativo": empresa["ativo"],
                    "created_at": created_at,
                    "updated_at": created_at,
                    "deleted_at": None,
                })
                self._usuario_ids.append(uid)
                uids.append(uid)
            self._empresa_usuario_map[eid] = uids

        # Oficina users
        for oid in self._oficina_ids:
            oficina = next(o for o in self.ds.oficinas if o["id"] == oid)
            n = random.randint(min_o, max_o)
            uids = []
            for j in range(n):
                uid = str(uuid.uuid4())
                role = "oficina_owner" if j == 0 else "oficina_user"
                created_at = oficina["created_at"]
                ultimo_login = _random_dt(
                    created_at + timedelta(days=1), self.end_dt
                ) if oficina["ativo"] else None
                self.ds.usuarios.append({
                    "id": uid,
                    "email": self._unique_email(),
                    "nome": fake.name(),
                    "telefone": fake.phone_number(),
                    "role": role,
                    "avatar_url": None,
                    "empresa_id": None,
                    "oficina_id": oid,
                    "ultimo_login": ultimo_login,
                    "login_count": random.randint(1, 150),
                    "ativo": oficina["ativo"],
                    "created_at": created_at,
                    "updated_at": created_at,
                    "deleted_at": None,
                })
                self._usuario_ids.append(uid)
                uids.append(uid)
            self._oficina_usuario_map[oid] = uids

        logger.info(f"  → {len(self.ds.usuarios)} usuarios")

    # -----------------------------------------------------------------------
    # 5. Certificacoes
    # -----------------------------------------------------------------------

    def gen_certificacoes(self) -> None:
        logger.info("Generating certificacoes...")
        cert_cfg = self.cfg["certificacoes"]

        for oficina in self.ds.oficinas:
            oid = oficina["id"]
            tier = oficina["tier"]
            # Higher tier offices have more certifications
            n_certs = {"bronze": 0, "prata": 1, "ouro": 2, "diamante": 3}[tier]
            n_certs = random.randint(n_certs, n_certs + 2)

            eligible_types = [
                ct for ct, ccfg in cert_cfg.items()
                if tier in ccfg.get("tiers", [tier])
            ]
            if not eligible_types:
                eligible_types = ["abvtex"]

            chosen = random.sample(eligible_types, min(n_certs, len(eligible_types)))
            cert_weights = [cert_cfg.get(ct, {}).get("weight", 0.1) for ct in eligible_types]

            for ct in chosen:
                issue_date = _random_dt(oficina["created_at"], self.end_dt).date()
                valid_months = random.choice([12, 24, 36])
                valid_date = issue_date + timedelta(days=valid_months * 30)
                ativo = valid_date > date.today()

                self.ds.certificacoes.append({
                    "id": str(uuid.uuid4()),
                    "oficina_id": oid,
                    "tipo": ct,
                    "nome": ct.upper().replace("_", " "),
                    "entidade_emissora": fake.company(),
                    "numero_certificado": f"{ct.upper()}-{random.randint(10000, 99999)}",
                    "data_emissao": issue_date,
                    "data_validade": valid_date,
                    "ativo": ativo,
                    "documento_url": None,
                    "verificado": random.random() < 0.80,
                    "data_verificacao": _random_dt(
                        _dt(datetime.combine(issue_date, datetime.min.time())),
                        self.end_dt
                    ) if random.random() < 0.80 else None,
                    "created_at": _dt(datetime.combine(issue_date, datetime.min.time())),
                    "updated_at": _dt(datetime.combine(issue_date, datetime.min.time())),
                })
        logger.info(f"  → {len(self.ds.certificacoes)} certificacoes")

    # -----------------------------------------------------------------------
    # 6. Pedidos + items + propostas + producao + pagamentos + avaliacoes
    # -----------------------------------------------------------------------

    def gen_pedidos_and_lifecycle(self) -> None:
        logger.info("Generating pedidos and full lifecycle...")
        n_total = self.cfg["pedidos_total"]
        funnel = self.cfg["funnel"]
        fin = self.cfg["financeiro"]
        sazon = self.cfg["sazonalidade"]
        month_keys = ["jan","feb","mar","apr","may","jun",
                      "jul","aug","sep","oct","nov","dec"]

        # Status machine
        statuses = [
            "rascunho","publicado","em_negociacao","confirmado",
            "em_producao","controle_qualidade","entregue","finalizado",
            "cancelado",
        ]

        # Get only active empresas
        active_empresas = [e for e in self.ds.empresas if e["ativo"]]
        if not active_empresas:
            active_empresas = self.ds.empresas

        pedido_counter = 0

        for _ in range(n_total):
            empresa = random.choice(active_empresas)
            eid = empresa["id"]
            cat_id = random.choice(self._categoria_ids)

            # Creation date: after empresa signup, with seasonality weight
            min_date = empresa["created_at"] + timedelta(days=3)
            if min_date >= self.end_dt:
                min_date = self.start_dt
            created_at = _random_dt(min_date, self.end_dt)
            month_key = month_keys[created_at.month - 1]
            # Apply seasonality as acceptance probability
            if random.random() > sazon[month_key]:
                continue  # Skip to simulate lower volume months

            pedido_counter += 1
            pid = str(uuid.uuid4())

            # Financial
            quantidade = random.randint(50, 5000)
            preco_medio = max(5.0, random.gauss(fin["preco_medio_peca"], fin["preco_desvio"]))
            valor_estimado = round(quantidade * preco_medio, 2)

            # Status progression
            status = "rascunho"
            oficina_id = None
            data_publicacao = None
            data_limite = None
            prazo_entrega = None
            data_entrega_real = None
            valor_final = None

            # Progress through funnel
            if random.random() < funnel["publicado_rate"]:
                status = "publicado"
                data_publicacao = _dt(created_at + timedelta(hours=random.uniform(1, 48)))
                data_limite = _dt(data_publicacao + timedelta(days=random.randint(3, 14)))
                prazo_entrega = (data_limite + timedelta(days=random.randint(20, 90))).date()

                if random.random() < funnel["match_rate"]:
                    status = "em_negociacao"
                    # Pick a matching oficina
                    matching_oficinas = [
                        o for o in self.ds.oficinas
                        if o["ativo"] and o["created_at"] <= created_at
                    ]
                    if matching_oficinas:
                        matched_oficina = random.choice(matching_oficinas)
                        oficina_id = matched_oficina["id"]
                        discount = 1 - fin["desconto_volume"] * (quantidade / 1000)
                        valor_final = round(valor_estimado * discount * random.uniform(0.85, 1.05), 2)

                        if random.random() < 0.90:
                            status = "confirmado"
                            if random.random() < funnel["producao_rate"]:
                                status = "em_producao"
                                if random.random() < 0.80:
                                    status = "controle_qualidade"
                                    if random.random() < funnel["entregue_rate"]:
                                        status = "entregue"
                                        data_entrega_real = (
                                            created_at + timedelta(days=random.randint(20, 100))
                                        ).date()
                                        if random.random() < funnel["finalizado_rate"]:
                                            status = "finalizado"

            # Random cancellation chance
            if status not in ("finalizado", "entregue") and random.random() < funnel["cancelado_rate"]:
                status = "cancelado"

            titulo_prefixes = ["Produção de", "Confecção de", "Fabricação de", "Lote de"]
            titulo_items = ["Camisetas", "Calças", "Vestidos", "Uniformes",
                            "Pijamas", "Shorts", "Blusas", "Jaquetas"]
            titulo = f"{random.choice(titulo_prefixes)} {quantidade} {random.choice(titulo_items)}"

            self.ds.pedidos.append({
                "id": pid,
                "codigo": f"PED-{created_at.year}-{pedido_counter:05d}",
                "empresa_id": eid,
                "oficina_id": oficina_id,
                "titulo": titulo,
                "descricao": fake.text(max_nb_chars=300),
                "categoria_id": cat_id,
                "quantidade_total": quantidade,
                "unidade": "peças",
                "valor_estimado": valor_estimado,
                "valor_final": valor_final,
                "moeda": "BRL",
                "data_publicacao": data_publicacao,
                "data_limite_propostas": data_limite,
                "prazo_entrega": prazo_entrega,
                "data_entrega_real": data_entrega_real,
                "status": status,
                "prioridade": random.randint(1, 5),
                "observacoes": fake.sentence() if random.random() < 0.4 else None,
                "anexos_urls": None,
                "created_at": created_at,
                "updated_at": created_at + timedelta(days=random.randint(0, 5)),
                "deleted_at": None,
            })

            # Pedido items
            self._gen_pedido_items(pid, quantidade, created_at)

            # Propostas (if order was published)
            if status not in ("rascunho",):
                self._gen_propostas(pid, oficina_id, data_publicacao or created_at, status)

            # Producao (if matched and in production stages)
            if oficina_id and status in ("em_producao","controle_qualidade","entregue","finalizado"):
                self._gen_producao(pid, oficina_id, created_at, status)

            # Pagamento (if finalizado)
            if status == "finalizado" and oficina_id and valor_final:
                self._gen_pagamento(pid, eid, oficina_id, valor_final, created_at, fin)

            # Avaliacao (if finalizado)
            if status == "finalizado" and oficina_id:
                self._gen_avaliacoes(pid, eid, oficina_id, created_at)

        logger.info(f"  → {len(self.ds.pedidos)} pedidos")
        logger.info(f"  → {len(self.ds.pedido_items)} pedido_items")
        logger.info(f"  → {len(self.ds.propostas)} propostas")
        logger.info(f"  → {len(self.ds.producao)} producao records")
        logger.info(f"  → {len(self.ds.pagamentos)} pagamentos")
        logger.info(f"  → {len(self.ds.avaliacoes)} avaliacoes")

    def _gen_pedido_items(self, pid: str, total_qty: int, base_dt: datetime) -> None:
        min_i, max_i = self.cfg["pedido_items_per_pedido"]
        n = random.randint(min_i, max_i)
        sizes = ["PP", "P", "M", "G", "GG", "XGG"]
        cores = ["Branco", "Preto", "Azul Marinho", "Cinza", "Verde", "Vermelho",
                 "Amarelo", "Rosa", "Bege", "Estampado"]
        materiais = ["Algodão", "Poliéster", "Malha", "Linho", "Viscose",
                     "Denim", "Nylon", "Elastano", "Modal"]

        qty_remaining = total_qty
        for i in range(n):
            qty = (qty_remaining // (n - i)) + random.randint(-5, 5) if i < n - 1 else qty_remaining
            qty = max(1, qty)
            qty_remaining -= qty
            self.ds.pedido_items.append({
                "id": str(uuid.uuid4()),
                "pedido_id": pid,
                "descricao": fake.sentence(nb_words=4),
                "quantidade": qty,
                "tamanho": random.choice(sizes),
                "cor": random.choice(cores),
                "material": random.choice(materiais),
                "valor_unitario": round(random.uniform(8, 45), 2),
                "observacoes": fake.sentence() if random.random() < 0.3 else None,
                "created_at": base_dt,
            })

    def _gen_propostas(self, pid: str, winning_oficina_id: str | None,
                       pub_dt: datetime, order_status: str) -> None:
        min_p, max_p = self.cfg["propostas_per_pedido"]
        n = random.randint(min_p, max_p)
        if n == 0:
            return

        # Pick n distinct oficinas to bid
        available = [o["id"] for o in self.ds.oficinas if o["ativo"]]
        if winning_oficina_id and winning_oficina_id not in available:
            available.append(winning_oficina_id)

        bidders = random.sample(available, min(n, len(available)))
        # Ensure winner is in bidders if applicable
        if winning_oficina_id and winning_oficina_id not in bidders and bidders:
            bidders[-1] = winning_oficina_id

        for oid in bidders:
            is_winner = (oid == winning_oficina_id) and (
                order_status in ("confirmado","em_producao","controle_qualidade","entregue","finalizado")
            )

            if is_winner:
                status = "aceita"
                data_resposta = _dt(pub_dt + timedelta(hours=random.uniform(2, 120)))
            elif order_status in ("finalizado","entregue","em_producao") and not is_winner:
                status = random.choice(["recusada", "expirada"])
                data_resposta = _dt(pub_dt + timedelta(hours=random.uniform(2, 72)))
            else:
                status = random.choice(["enviada", "em_analise", "recusada", "expirada", "retirada"])
                data_resposta = _dt(pub_dt + timedelta(hours=random.uniform(1, 168))) if status in ("recusada","expirada") else None

            proposta_dt = _dt(pub_dt + timedelta(hours=random.uniform(0.5, 72)))

            self.ds.propostas.append({
                "id": str(uuid.uuid4()),
                "pedido_id": pid,
                "oficina_id": oid,
                "valor_proposto": round(random.uniform(5000, 50000), 2),
                "prazo_proposto": (proposta_dt + timedelta(days=random.randint(14, 60))).date(),
                "descricao": fake.text(max_nb_chars=200),
                "condicoes": fake.sentence() if random.random() < 0.5 else None,
                "status": status,
                "data_resposta": data_resposta,
                "motivo_recusa": fake.sentence() if status == "recusada" else None,
                "created_at": proposta_dt,
                "updated_at": proposta_dt + timedelta(hours=random.randint(1, 24)),
            })

    def _gen_producao(self, pid: str, oid: str, order_dt: datetime, order_status: str) -> None:
        status_map = {
            "em_producao": "em_costura",
            "controle_qualidade": "controle_qualidade",
            "entregue": "expedido",
            "finalizado": "expedido",
        }
        prod_status = status_map.get(order_status, "em_costura")
        pct = {
            "aguardando_material": random.uniform(0, 5),
            "em_corte": random.uniform(10, 25),
            "em_costura": random.uniform(30, 70),
            "em_acabamento": random.uniform(70, 90),
            "controle_qualidade": random.uniform(90, 98),
            "embalagem": random.uniform(95, 99),
            "expedido": 100.0,
        }.get(prod_status, 50.0)

        total_qty = next(p["quantidade_total"] for p in self.ds.pedidos if p["id"] == pid)
        produced = int(total_qty * pct / 100)
        approved = int(produced * random.uniform(0.92, 0.99))
        rejected = produced - approved

        self.ds.producao.append({
            "id": str(uuid.uuid4()),
            "pedido_id": pid,
            "oficina_id": oid,
            "status": prod_status,
            "percentual_concluido": round(pct, 2),
            "quantidade_produzida": produced,
            "quantidade_aprovada": approved,
            "quantidade_rejeitada": rejected,
            "data_inicio": _dt(order_dt + timedelta(days=random.randint(2, 10))),
            "data_previsao": (order_dt + timedelta(days=random.randint(20, 60))).date(),
            "data_conclusao": _dt(order_dt + timedelta(days=random.randint(15, 80))) if prod_status == "expedido" else None,
            "observacoes_qualidade": fake.sentence() if random.random() < 0.3 else None,
            "fotos_producao": None,
            "created_at": _dt(order_dt + timedelta(days=2)),
            "updated_at": _dt(order_dt + timedelta(days=random.randint(3, 15))),
        })

    def _gen_pagamento(self, pid: str, eid: str, oid: str,
                       valor_final: float, order_dt: datetime, fin: dict) -> None:
        taxa_pct = round(random.uniform(fin["taxa_plataforma_min"], fin["taxa_plataforma_max"]), 4)
        taxa = round(valor_final * taxa_pct, 2)
        liquido = round(valor_final - taxa, 2)
        metodos = ["pix", "boleto", "transferencia", "cartao_credito"]
        metodo_pesos = [0.55, 0.25, 0.15, 0.05]
        pag_dt = _dt(order_dt + timedelta(days=random.randint(1, 30)))

        self.ds.pagamentos.append({
            "id": str(uuid.uuid4()),
            "pedido_id": pid,
            "empresa_id": eid,
            "oficina_id": oid,
            "valor_bruto": valor_final,
            "taxa_plataforma": taxa,
            "valor_liquido": liquido,
            "percentual_taxa": round(taxa_pct * 100, 2),
            "metodo": _weighted_choice(metodos, metodo_pesos),
            "status": "pago",
            "referencia_externa": f"TXL-{uuid.uuid4().hex[:12].upper()}",
            "comprovante_url": None,
            "data_vencimento": (order_dt + timedelta(days=5)).date(),
            "data_pagamento": pag_dt,
            "created_at": order_dt,
            "updated_at": pag_dt,
        })

    def _gen_avaliacoes(self, pid: str, eid: str, oid: str, order_dt: datetime) -> None:
        empresa = next(e for e in self.ds.empresas if e["id"] == eid)
        oficina_obj = next(o for o in self.ds.oficinas if o["id"] == oid)

        empresa_usuario_id = self._empresa_usuario_map.get(eid, [None])[0]
        oficina_usuario_id = self._oficina_usuario_map.get(oid, [None])[0]

        aval_dt = _dt(order_dt + timedelta(days=random.randint(3, 14)))

        # Empresa reviews oficina
        if empresa_usuario_id and random.random() < 0.75:
            q_score = oficina_obj["score_qualidade"] or 7.0
            nota_base = min(5, max(1, round(q_score / 2)))
            self.ds.avaliacoes.append({
                "id": str(uuid.uuid4()),
                "pedido_id": pid,
                "avaliador_id": empresa_usuario_id,
                "avaliado_empresa_id": None,
                "avaliado_oficina_id": oid,
                "nota_geral": nota_base,
                "nota_qualidade": max(1, min(5, nota_base + random.randint(-1, 1))),
                "nota_pontualidade": max(1, min(5, nota_base + random.randint(-1, 1))),
                "nota_comunicacao": max(1, min(5, nota_base + random.randint(-1, 1))),
                "nota_custo_beneficio": max(1, min(5, nota_base + random.randint(-1, 1))),
                "comentario": fake.text(max_nb_chars=200) if random.random() < 0.6 else None,
                "publica": random.random() < 0.85,
                "created_at": aval_dt,
            })

    # -----------------------------------------------------------------------
    # 7. Mensagens
    # -----------------------------------------------------------------------

    def gen_mensagens(self) -> None:
        logger.info("Generating mensagens...")
        # Generate messages for matched orders
        matched_pedidos = [p for p in self.ds.pedidos if p["oficina_id"] is not None]

        for pedido in random.sample(matched_pedidos, min(len(matched_pedidos), 800)):
            eid = pedido["empresa_id"]
            oid = pedido["oficina_id"]
            empresa_users = self._empresa_usuario_map.get(eid, [])
            oficina_users = self._oficina_usuario_map.get(oid, [])

            if not empresa_users or not oficina_users:
                continue

            n_msgs = random.randint(2, 15)
            base_dt = pedido["created_at"]

            for i in range(n_msgs):
                is_empresa_sender = i % 2 == 0
                sender = random.choice(empresa_users) if is_empresa_sender else random.choice(oficina_users)
                recipient = random.choice(oficina_users) if is_empresa_sender else random.choice(empresa_users)

                msg_dt = _dt(base_dt + timedelta(hours=random.randint(i * 2, i * 2 + 48)))
                lida = random.random() < 0.80

                self.ds.mensagens.append({
                    "id": str(uuid.uuid4()),
                    "remetente_id": sender,
                    "destinatario_id": recipient,
                    "pedido_id": pedido["id"],
                    "conteudo": fake.text(max_nb_chars=300),
                    "lida": lida,
                    "data_leitura": _dt(msg_dt + timedelta(hours=random.uniform(0.1, 24))) if lida else None,
                    "created_at": msg_dt,
                })
        logger.info(f"  → {len(self.ds.mensagens)} mensagens")

    # -----------------------------------------------------------------------
    # 8. Eventos plataforma (clickstream)
    # -----------------------------------------------------------------------

    def gen_eventos(self) -> None:
        logger.info("Generating eventos_plataforma...")
        n = self.cfg["eventos_total"]
        tipos = [
            "page_view", "login", "search_performed", "oficina_viewed",
            "pedido_created", "pedido_published", "proposta_sent",
            "proposta_viewed", "mensagem_sent", "pagamento_initiated",
            "avaliacao_submitted", "relatorio_viewed", "logout",
        ]
        tipo_pesos = [0.30, 0.12, 0.12, 0.10, 0.05, 0.04, 0.05, 0.06, 0.07, 0.03, 0.02, 0.02, 0.02]
        dispositivos = ["desktop", "mobile", "tablet"]
        disp_pesos = [0.55, 0.35, 0.10]
        paginas = ["/dashboard", "/pedidos", "/oficinas", "/propostas",
                   "/pagamentos", "/relatorios", "/perfil", "/buscar"]

        active_users = [u for u in self.ds.usuarios if u["ativo"] and u["role"] != "admin"]

        for _ in range(n):
            user = random.choice(active_users)
            tipo = _weighted_choice(tipos, tipo_pesos)
            ev_dt = _random_dt(user["created_at"], self.end_dt)

            self.ds.eventos_plataforma.append({
                "id": str(uuid.uuid4()),
                "usuario_id": user["id"],
                "session_id": f"sess_{uuid.uuid4().hex[:16]}",
                "tipo": tipo,
                "pagina": random.choice(paginas),
                "referrer": None,
                "entidade_tipo": None,
                "entidade_id": None,
                "metadata": "{}",
                "ip_address": fake.ipv4(),
                "user_agent": fake_en.user_agent(),
                "dispositivo": _weighted_choice(dispositivos, disp_pesos),
                "created_at": ev_dt,
            })
        logger.info(f"  → {len(self.ds.eventos_plataforma)} eventos")

    # -----------------------------------------------------------------------
    # 9. Notificacoes
    # -----------------------------------------------------------------------

    def gen_notificacoes(self) -> None:
        logger.info("Generating notificacoes...")
        tipos_notif = [
            ("pedido_update", "Pedido Atualizado"),
            ("proposta_nova", "Nova Proposta Recebida"),
            ("pagamento", "Pagamento Processado"),
            ("sistema", "Mensagem do Sistema"),
        ]
        canais = ["plataforma", "email", "push"]
        canal_pesos = [0.60, 0.30, 0.10]

        active_users = [u for u in self.ds.usuarios if u["ativo"]]
        n_notif = min(3000, len(active_users) * 5)

        for _ in range(n_notif):
            user = random.choice(active_users)
            tipo, titulo = random.choice(tipos_notif)
            lida = random.random() < 0.65
            created_at = _random_dt(user["created_at"], self.end_dt)

            self.ds.notificacoes.append({
                "id": str(uuid.uuid4()),
                "usuario_id": user["id"],
                "titulo": titulo,
                "conteudo": fake.sentence(),
                "tipo": tipo,
                "canal": _weighted_choice(canais, canal_pesos),
                "entidade_tipo": None,
                "entidade_id": None,
                "lida": lida,
                "data_leitura": _dt(created_at + timedelta(hours=random.uniform(0.1, 72))) if lida else None,
                "created_at": created_at,
            })
        logger.info(f"  → {len(self.ds.notificacoes)} notificacoes")

    # -----------------------------------------------------------------------
    # Orchestrator
    # -----------------------------------------------------------------------

    def generate_all(self) -> TexlinkDataset:
        logger.info("=" * 60)
        logger.info("Starting Texlink seed data generation")
        logger.info("=" * 60)

        self.gen_categorias()
        self.gen_empresas()
        self.gen_oficinas()
        self.gen_usuarios()
        self.gen_certificacoes()
        self.gen_pedidos_and_lifecycle()
        self.gen_mensagens()
        self.gen_eventos()
        self.gen_notificacoes()

        logger.info("=" * 60)
        logger.info("Seed generation complete!")
        self._print_summary()
        return self.ds

    def _print_summary(self) -> None:
        totals = {
            "categorias": len(self.ds.categorias),
            "empresas": len(self.ds.empresas),
            "oficinas": len(self.ds.oficinas),
            "usuarios": len(self.ds.usuarios),
            "pedidos": len(self.ds.pedidos),
            "pedido_items": len(self.ds.pedido_items),
            "propostas": len(self.ds.propostas),
            "producao": len(self.ds.producao),
            "avaliacoes": len(self.ds.avaliacoes),
            "certificacoes": len(self.ds.certificacoes),
            "pagamentos": len(self.ds.pagamentos),
            "mensagens": len(self.ds.mensagens),
            "eventos_plataforma": len(self.ds.eventos_plataforma),
            "notificacoes": len(self.ds.notificacoes),
        }
        for table, count in totals.items():
            logger.info(f"  {table:<25} {count:>6} rows")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "src/seeds/seed_config.yaml"
    cfg = load_config(config_path)
    seeder = TexlinkSeeder(cfg)
    dataset = seeder.generate_all()
