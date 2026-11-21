# Starter kit — Projeto Integrador (Sistemas Distribuídos e Computação em Nuvem)

Ponto de partida **opcional** para a Plataforma Distribuída de Inferência de
ML. Ele entrega um serviço de inferência mínimo e a infraestrutura de
desenvolvimento, para o grupo começar pela arquitetura e não pela
configuração. O **barema** avalia o que o grupo acrescenta a esta base: os
pontos marcados com `TODO(...)`, os serviços que faltam e as decisões
documentadas no README do grupo.

| Já vem pronto | Fica com o grupo |
|---|---|
| Serviço de inferência (FastAPI) com modelo *mock* determinístico, `/predict`, `/healthz`, `/readyz` e `/metrics` (Prometheus) | Trocar o *mock* por um modelo real (opcional); cache no Redis (`TODO(Checkpoint 2)`) |
| `Dockerfile` do serviço (imagem fixada, usuário sem privilégio) | `Dockerfile` dos demais serviços |
| `docker-compose.yml` com Redis, RabbitMQ e PostgreSQL | API Gateway (auth JWT), serviço de API/pedidos, *worker*, pilha de observabilidade |
| Manifesto Kubernetes de exemplo (Deployment + Service com *probes* e *requests*) | Manifestos dos demais serviços, Ingress ou Gateway API, ConfigMap/Secret e **HPA** |
| Gerador de carga (`tools/loadgen.py`) | Resiliência, coordenação distribuída, *tracing* e logs estruturados |

## Pré-requisitos

- Docker com Compose v2 (`docker compose version`).
- Python 3.12 (só para o gerador de carga).
- Para Kubernetes: `kubectl` e **kind** ou **minikube**.

## Como subir (Docker Compose)

```sh
cp .env.example .env              # credenciais locais de desenvolvimento
docker compose up -d --build --wait

curl -s localhost:8000/predict -H 'Content-Type: application/json' \
     -d '{"text": "o pedido chegou rápido"}'
curl -s localhost:8000/metrics | grep predictions_total
python3.12 tools/loadgen.py --duration 20
```

| Serviço | Porta | Observação |
|---|---|---|
| `inference` | 8000 | documentação interativa em `/docs` |
| `cache` (Redis) | --- | `cache:6379` na rede do Compose |
| `broker` (RabbitMQ) | 15672 | AMQP em `broker:5672`; painel em `http://localhost:15672` |
| `history-db` (PostgreSQL) | --- | `history-db:5432`; banco do serviço de histórico |

Só as portas de entrada são publicadas no *host*, o que evita conflito com um
Redis ou PostgreSQL já instalado na máquina. Os serviços se encontram pelo
nome. Se precisar acessar um deles de fora, acrescente `ports:` no Compose.

Para parar: `docker compose down`. Para também apagar os dados:
`docker compose down -v`.

O RabbitMQ é só uma opção. Se o grupo preferir Kafka, use a imagem oficial
`apache/kafka` em modo KRaft (sem ZooKeeper) e justifique a escolha.

## Como implantar (Kubernetes local)

A imagem é construída localmente, então precisa ser **carregada no cluster**:

```sh
docker compose build inference              # gera inference:0.1.0

# kind
kind create cluster --name sdcn
kind load docker-image inference:0.1.0 --name sdcn
# ou minikube
minikube start
minikube image load inference:0.1.0

kubectl apply -f k8s/
kubectl rollout status deployment/inference
kubectl port-forward service/inference 8000:80
```

Cuidados que costumam travar os grupos:

- **Nunca use a tag `:latest`.** Com ela, o Kubernetes tenta baixar a imagem
  de um registro e o *pod* fica em `ErrImagePull`. Troque a tag a cada versão
  (`0.1.0`, `0.2.0`...) e carregue de novo no cluster.
- **HPA precisa de métricas.** No minikube: `minikube addons enable
  metrics-server`. No kind, instale o metrics-server e acrescente o argumento
  `--kubelet-insecure-tls` ao contêiner dele. Sem `resources.requests.cpu`, o
  HPA não calcula a utilização.
- **Controlador de entrada.** O ingress-nginx foi aposentado pelo projeto
  Kubernetes em março de 2026 e não recebe mais correções; isso inclui o
  *addon* `ingress` do minikube, que o usa. Prefira um controlador mantido
  que implemente Ingress e **Gateway API** (ex.: Traefik, instalado via Helm)
  e justifique a escolha. Gateway API (`Gateway` + `HTTPRoute`) vale como
  Ingress no barema. No kind, crie o cluster com `extraPortMappings` para
  expor as portas 80/443 no *host*.
- **Gere carga para ver a escala:** com o `port-forward` ativo, rode
  `python3.12 tools/loadgen.py --concurrency 16 --duration 180` e acompanhe
  `kubectl get hpa -w`. A variável `CPU_WORK_MS` controla o custo de cada
  predição.

## Evolução por marco

- **Checkpoint 1 (Semana 10):** proposta de arquitetura. Decida quais
  serviços existirão, como se comunicam e onde fica cada dado.
- **Checkpoint 2 (Semana 14):** todos os serviços rodando no Compose,
  incluindo cache, fluxo assíncrono pelo broker e *readiness* real.
- **Entrega final (Semana 19):** Kubernetes com HPA, gateway com
  autenticação, resiliência, coordenação, observabilidade (métricas,
  logs e *traces*) e segredos fora do código.

> As credenciais em `.env.example` são **apenas para desenvolvimento local**.
> Não as reutilize fora da sua máquina e nunca versione o `.env`.
