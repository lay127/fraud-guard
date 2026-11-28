# FraudGuard

Plataforma distribuída de inferência para **detecção de fraude em transações
com cartão**. Projeto Integrador da disciplina Sistemas Distribuídos e
Computação em Nuvem (Ciência de Dados e Inteligência Artificial, PUC Minas).

Para cada transação recebida, o sistema prediz se ela é **legítima** ou
**suspeita de fraude** e devolve um *score* de risco e a versão do modelo. As
transações podem ser avaliadas de forma **síncrona** (autorização em tempo
real) ou enviadas em **lotes assíncronos** para reanálise em segundo plano. O
serviço de inferência escala conforme a carga, o histórico de predições fica
persistido e resultados repetidos são servidos do cache.

> Status: **Checkpoint 2** (serviços no Docker Compose). Infraestrutura
> (Kafka, PostgreSQL e Redis) e inferência prontas; gateway, API de
> transações e worker em implementação.

## Stack

Escolhida pelo grupo (detalhes e justificativas na proposta e no relatório):

- Serviços em Python (FastAPI), com Docker e Docker Compose para desenvolvimento
- Kubernetes (kind ou minikube) com HPA no serviço de inferência
- Mensageria: Apache Kafka
- Dados: PostgreSQL (banco por serviço) e Redis (cache)
- Observabilidade: Prometheus, Grafana e OpenTelemetry
- CI: GitHub Actions

## Estrutura do repositório

```
fraud-guard/
├── services/
│   ├── inference/      # serviço de inferência (base do starter kit)
│   ├── gateway/        # API Gateway: autenticação, roteamento, rate limiting
│   ├── api/            # API de pedidos: recebe lotes e registra o histórico
│   └── worker/         # consumidor do broker que processa os lotes
├── k8s/                # manifestos Kubernetes
├── observability/      # configuração de Prometheus, Grafana e OpenTelemetry
├── tools/              # utilitários (gerador de carga)
├── docs/
│   ├── proposta/       # proposta do Checkpoint 1 e diagrama
│   └── starter-kit.md  # README original do starter kit
├── .github/workflows/  # pipelines de CI
├── docker-compose.yml
└── .env.example
```

## Como subir (Docker Compose)

Pré-requisitos: Docker com Compose v2 (`docker compose version`) e Python 3.12
(só para o gerador de carga).

```sh
cp .env.example .env               # segredos locais (o .env não é versionado)
docker compose up -d --build --wait
docker compose ps                  # tudo "healthy"; kafka-init "Exited (0)"
```

O `--wait` só termina quando todos os *healthchecks* passam. A ordem de
subida é controlada por `depends_on`: o Kafka fica saudável, o `kafka-init`
cria os tópicos e só então sobem os serviços que dependem deles.

| Serviço | Porta no host | Na rede do Compose | Papel |
|---|---|---|---|
| `inference` | 8000 | `inference:8000` | Inferência (score de fraude); docs em `/docs` |
| `cache` (Redis 7.4) | --- | `cache:6379` | Cache de predições e lock distribuído (com senha) |
| `kafka` (Kafka 4.3, KRaft) | --- | `kafka:9092` | Broker do fluxo assíncrono |
| `kafka-init` | --- | --- | Cria os tópicos `transacoes.lote` (3 partições) e `transacoes.lote.dlq` e termina |
| `transacoes-db` (PostgreSQL 17) | --- | `transacoes-db:5432` | `db_transacoes`, dono: Serviço de Transações |
| `predicoes-db` (PostgreSQL 17) | --- | `predicoes-db:5432` | `db_predicoes`, dono: Worker de Fraude |
| `gateway` | 8080 | `gateway:8000` | API Gateway (perfil `servicos`) |
| `api` | --- | `api:8000` | Serviço de Transações (perfil `servicos`) |
| `worker` | --- | --- | Worker de Fraude (perfil `servicos`) |

Os três últimos ficam no perfil `servicos` até terem Dockerfile. Para subir
tudo junto: `docker compose --profile servicos up -d --build --wait`. Quando
um serviço estiver pronto, basta tirar a linha `profiles` dele no
`docker-compose.yml`.

### Testes rápidos

```sh
# Inferência
curl -s localhost:8000/predict -H 'Content-Type: application/json' \
     -d '{"text": "exemplo"}'
python3.12 tools/loadgen.py --duration 20

# Redis (a senha vem do .env)
docker compose exec cache redis-cli ping

# Kafka: listar tópicos, publicar e consumir uma mensagem
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
echo '{"lote_id":"teste"}' | docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic transacoes.lote
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic transacoes.lote --from-beginning --max-messages 1

# PostgreSQL
docker compose exec transacoes-db psql -U transacoes -d transacoes -c 'select 1'
docker compose exec predicoes-db psql -U predicoes -d predicoes -c 'select 1'
```

Para parar: `docker compose down` (ou `docker compose down -v` para apagar os
dados). Instruções de Kubernetes e cuidados comuns estão em
[docs/starter-kit.md](docs/starter-kit.md).

### Segredos e versões

- Senhas, `JWT_SECRET` e o ID do cluster Kafka ficam no `.env`, que está no
  `.gitignore`. O `.env.example` (versionado) traz valores só de
  desenvolvimento local; cada pessoa copia e ajusta.
- As versões das imagens são fixadas no `.env` (`REDIS_VERSION`,
  `KAFKA_VERSION`, `POSTGRES_VERSION`) e as imagens do grupo usam tag
  `0.1.0`. Nunca use `:latest`.
- Variáveis já disponíveis para os serviços do grupo: `DATABASE_URL`,
  `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC_LOTES`, `KAFKA_TOPIC_DLQ`,
  `KAFKA_CONSUMER_GROUP`, `INFERENCE_URL`, `REDIS_URL` e `JWT_SECRET` (veja
  cada serviço no `docker-compose.yml`).

### Por que Kafka no lugar do RabbitMQ do starter kit

O fluxo assíncrono processa lotes de transações que precisam ser
reprocessáveis e auditáveis. O Kafka guarda as mensagens num log
persistente (dá para reler um lote), particiona o tópico para vários
workers consumirem em paralelo no mesmo *consumer group* e roda em modo
KRaft, sem ZooKeeper, o que mantém o Compose leve.

### Checkpoint 2

A tag `checkpoint-2` marca o commit demonstrado em sala. Ela deve ser criada
quando gateway, API e worker estiverem rodando no Compose:

```sh
git tag -a checkpoint-2 -m "Checkpoint 2: serviços no Docker Compose"
git push origin checkpoint-2
```

## Marcos

| Marco | Entrega | Tag |
|---|---|---|
| Checkpoint 1 (Semana 10) | Proposta de arquitetura (1 página + diagrama) | `checkpoint-1` |
| Checkpoint 2 (Semana 14) | Serviços rodando no Docker Compose | `checkpoint-2` |
| Entrega final (Semana 19) | Código, manifestos, relatório e demonstração | `entrega-final` |
