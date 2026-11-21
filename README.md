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

> Status: **Checkpoint 1** (proposta de arquitetura). Os serviços além da
> inferência ainda não foram implementados.

## Stack

Escolhida pelo grupo (detalhes e justificativas na proposta e no relatório):

- Serviços em Python (FastAPI), com Docker e Docker Compose para desenvolvimento
- Kubernetes (kind ou minikube) com HPA no serviço de inferência
- Mensageria: Apache Kafka
- Dados: PostgreSQL (banco por serviço) e Redis (cache)
- Observabilidade: Prometheus, Grafana e OpenTelemetry
- CI: GitHub Actions

> O `docker-compose.yml` ainda é o do *starter kit* da disciplina, que usa
> RabbitMQ. A troca para Kafka faz parte dos próximos passos.

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

## Como executar (Docker Compose)

Pré-requisitos: Docker com Compose v2 e Python 3.12 (para o gerador de carga).

```sh
cp .env.example .env
docker compose up -d --build --wait

curl -s localhost:8000/predict -H 'Content-Type: application/json' \
     -d '{"text": "exemplo"}'
python3.12 tools/loadgen.py --duration 20
```

Para parar: `docker compose down` (ou `docker compose down -v` para apagar os
dados). Instruções de Kubernetes e cuidados comuns estão em
[docs/starter-kit.md](docs/starter-kit.md).

> As credenciais de `.env.example` são só para desenvolvimento local. Nunca
> versione o arquivo `.env`.

## Marcos

| Marco | Entrega | Tag |
|---|---|---|
| Checkpoint 1 (Semana 10) | Proposta de arquitetura (1 página + diagrama) | `checkpoint-1` |
| Checkpoint 2 (Semana 14) | Serviços rodando no Docker Compose | `checkpoint-2` |
| Entrega final (Semana 19) | Código, manifestos, relatório e demonstração | `entrega-final` |
