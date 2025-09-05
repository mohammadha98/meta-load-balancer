# Meta Load Balancer

An intelligent system for managing traffic load using machine learning that automatically changes the load balancing algorithm based on system metrics.

## System Architecture

- **Node.js Services (svc1, svc2, svc3)**: Three simple microservices, each returning a JSON with the service name and timestamp.
- **Nginx**: Acts as the main load balancer that distributes traffic between services.
- **Meta-Load-Balancer**: An intelligent Python service that uses machine learning to select the appropriate load balancing algorithm.
- **Prometheus**: For collecting system metrics.
- **Grafana**: For displaying metrics and system status.
- **Locust**: For traffic simulation and system testing.

## How to Run

```bash
git clone https://github.com/mohammadha98/meta-load-balancer.git
cd meta-load-balancer
docker-compose up --build
```

## Accessing Services

- **Main Website**: http://localhost:80
- **Grafana**: http://localhost:3000 (username: admin, password: admin)
- **Prometheus**: http://localhost:9090
- **Locust UI**: http://localhost:8089

## How It Works

1. The Meta-Load-Balancer service reads system metrics from Prometheus every 5 seconds.
2. Using the ML model, it predicts the appropriate load balancing algorithm.
3. It updates the `algo.conf` file and reloads Nginx.
4. Supported algorithms: round-robin, least_conn, and ip_hash.

## Detailed Usage Guide

### Initial Setup

After starting the system with `docker-compose up --build`, all services will be initialized. The system includes:

1. **Three backend services** (svc1, svc2, svc3) that simulate your application servers
2. **Load balancer** (Nginx) that distributes traffic to these services
3. **Monitoring stack** (Prometheus, Grafana, Node-exporter) for metrics collection and visualization
4. **Meta-load-balancer** that makes intelligent decisions about which load balancing algorithm to use
5. **Locust** for generating test traffic

### Traffic Generation and Testing

To test the system, navigate to the Locust UI at http://localhost:8089 and start a new test:

1. Enter the number of users to simulate
2. Set the spawn rate (users per second)
3. Enter the host URL (http://localhost:80)
4. Click "Start swarming"

Locust will generate traffic according to your specifications, allowing you to observe how the Meta-Load-Balancer responds to different traffic patterns.

### Monitoring System Performance

Access the Grafana dashboard at http://localhost:3000 to monitor:

1. **System metrics**: CPU and memory usage from node-exporter
2. **Application metrics**: HTTP latency and throughput from Prometheus
3. **Load balancing algorithm**: Current active algorithm selected by the Meta-Load-Balancer

The dashboard provides real-time visibility into how the system performs under different load conditions and which load balancing algorithm is currently active.

### Understanding Algorithm Selection

The Meta-Load-Balancer selects algorithms based on the following metrics:

- **CPU usage**: System processor utilization
- **Memory usage**: System memory consumption
- **HTTP latency**: Response time for requests
- **Throughput**: Number of requests processed per second

Based on these metrics, the ML model selects the most appropriate algorithm:

- **Round-robin**: Distributes requests sequentially across servers (good for homogeneous servers with similar workloads)
- **Least connections**: Directs traffic to the server with the fewest active connections (good for requests with varying processing times)
- **IP hash**: Consistently routes requests from the same client IP to the same server (good for session persistence)

## Grafana Dashboard

The Grafana dashboard includes the following panels:
- CPU and Memory from node-exporter
- HTTP latency and throughput from Prometheus
- Current load balancing algorithm display

## Retraining the ML Model

To retrain the model with new data:

```powershell
docker-compose run data-gen
# After data collection is complete:
docker-compose run model-trainer
# Then restart the meta-lb service:
docker-compose up -d --build meta-lb
```

### Data Collection Process

The data collection process involves:

1. Running different traffic scenarios against each load balancing algorithm
2. Collecting performance metrics during each test
3. Determining which algorithm performed best for each scenario
4. Saving this data to train the machine learning model

### Scenarios
- `ramp`: Gradually increasing traffic - tests how algorithms handle growing load
- `spike`: Sudden burst of traffic - tests how algorithms handle unexpected traffic surges
- `steady_high`: Constant high load - tests sustained performance under heavy traffic
- `steady_low`: Constant low load - tests baseline performance

### Data Collection Window
- For each scenario, each load balancing algorithm is tested for a fixed window (default: 10 seconds) after Nginx reload.
- Metrics are collected from Prometheus after the window.

### Label Definition
- For each scenario, the algorithm with the lowest average latency is selected as the label for that sample.
- This creates a supervised learning dataset where system metrics are mapped to the best-performing algorithm.

### Dataset Format
- `dataset.csv` columns: `cpu,mem,latency,p95,throughput,connections,label`
- These features are used to train the RandomForest classifier that powers the Meta-Load-Balancer.

### Customizing the Model

To customize the machine learning model:

1. Modify the `train_model.py` script to adjust hyperparameters or try different algorithms
2. Update the `generate_dataset.py` script to collect additional metrics or test different scenarios
3. Retrain the model using the commands above

## Sample Git Commands

```powershell
git add generate_dataset.py train_model.py meta-lb/requirements.txt docker-compose.yml README.md
# Commit your changes
git commit -m "feat: add supervised data-collection & model-training pipeline"
# Push to main branch
git push origin main
```

## Advanced Configuration

### Adding New Services

To add new backend services:

1. Create a new service directory with Dockerfile and application code
2. Add the service to docker-compose.yml
3. Update the Nginx configuration to include the new service
4. Restart the system with `docker-compose up --build`

### Modifying Load Balancing Algorithms

To add or modify load balancing algorithms:

1. Update the `LB_ALGORITHMS` dictionary in `generate_dataset.py`
2. Update the `algorithms` dictionary in `meta-lb/app.py`
3. Regenerate the dataset and retrain the model

