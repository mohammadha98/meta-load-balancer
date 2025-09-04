import time
import os
import subprocess
import requests
import joblib
import numpy as np
from prometheus_client import start_http_server, Gauge

# Define Prometheus metrics
ALGORITHM_GAUGE = Gauge('current_lb_algorithm', 'Current Load Balancing Algorithm', ['algorithm'])

# Initialize gauges for each algorithm
ALGORITHM_GAUGE.labels(algorithm='round-robin').set(0)
ALGORITHM_GAUGE.labels(algorithm='least_conn').set(0)
ALGORITHM_GAUGE.labels(algorithm='ip_hash').set(0)

# Load the ML model
def load_model():
    # Directly load the trained model from models/lb_model.pkl
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'lb_model.pkl')
    return joblib.load(model_path)

# Get metrics from Prometheus
def get_metrics():
    try:
        # Get CPU usage from node-exporter
        cpu_response = requests.get('http://prometheus:9090/api/v1/query', params={
            'query': '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'
        })
        cpu_data = cpu_response.json()
        cpu_usage = float(cpu_data['data']['result'][0]['value'][1]) if cpu_data['data']['result'] else 50.0
        
        # Get memory usage from node-exporter
        mem_response = requests.get('http://prometheus:9090/api/v1/query', params={
            'query': '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100'
        })
        mem_data = mem_response.json()
        mem_usage = float(mem_data['data']['result'][0]['value'][1]) if mem_data['data']['result'] else 50.0
        
        # Get HTTP latency from Nginx metrics
        latency_response = requests.get('http://prometheus:9090/api/v1/query', params={
            'query': 'sum(rate(nginx_http_request_duration_seconds_sum[1m])) / sum(rate(nginx_http_request_duration_seconds_count[1m]))'
        })
        latency_data = latency_response.json()
        latency = float(latency_data['data']['result'][0]['value'][1]) if latency_data['data']['result'] else 0.1
        
        # Get HTTP throughput from Nginx metrics
        throughput_response = requests.get('http://prometheus:9090/api/v1/query', params={
            'query': 'sum(rate(nginx_http_requests_total[1m]))'
        })
        throughput_data = throughput_response.json()
        throughput = float(throughput_data['data']['result'][0]['value'][1]) if throughput_data['data']['result'] else 10.0
        
        # Normalize values between 0 and 1
        cpu_usage = min(cpu_usage / 100.0, 1.0)
        mem_usage = min(mem_usage / 100.0, 1.0)
        latency = min(latency / 1.0, 1.0)  # Assuming 1 second is the max latency
        throughput = min(throughput / 100.0, 1.0)  # Assuming 100 req/s is the max throughput
        
        return np.array([[cpu_usage, mem_usage, latency, throughput]])
    except Exception as e:
        print(f"Error getting metrics: {e}")
        # Return default values if there's an error
        return np.array([[0.5, 0.5, 0.5, 0.5]])

# Update the Nginx configuration based on the predicted algorithm
def update_nginx_config(algorithm_id):
    algorithms = {
        0: "round-robin",
        1: "least_conn",
        2: "ip_hash"
    }
    
    algorithm = algorithms.get(algorithm_id, "round-robin")
    
    # Update Prometheus gauge
    for alg in algorithms.values():
        if alg == algorithm:
            ALGORITHM_GAUGE.labels(algorithm=alg).set(1)
        else:
            ALGORITHM_GAUGE.labels(algorithm=alg).set(0)
    
    # Generate new algo.conf content for server directives only
    server_content = "# Load balancing algorithm: " + algorithm + "\nserver svc1:80;\nserver svc2:80;\nserver svc3:80;\n"
    
    # Write server directives to algo.conf
    with open('/etc/nginx/conf.d/algo.conf', 'w') as f:
        f.write(server_content)
    
    # Update default.conf with the appropriate algorithm directive
    with open('/etc/nginx/conf.d/default.conf', 'r') as f:
        default_conf = f.read()
    
    # Remove any existing algorithm directives
    default_conf = default_conf.replace("least_conn;", "# least_conn;")
    default_conf = default_conf.replace("ip_hash;", "# ip_hash;")
    
    # Add the appropriate algorithm directive
    if algorithm == "least_conn":
        default_conf = default_conf.replace("# least_conn;", "least_conn;")
    elif algorithm == "ip_hash":
        default_conf = default_conf.replace("# ip_hash;", "ip_hash;")
    
    # Write the updated default.conf
    with open('/etc/nginx/conf.d/default.conf', 'w') as f:
        f.write(default_conf)
    
    # Prepare the JSON payload for the load balancer
    payload = {
        "algorithm": algorithm,
        "backends": ["svc1:3000", "svc2:3000", "svc3:3000"]
    }

    # Send the configuration to the load balancer
    try:
        response = requests.post("http://lb:7000/config", json=payload)
        response.raise_for_status()
        print(f"Updated load balancing algorithm to: {algorithm}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to update load balancer configuration: {e}")

    # Start Prometheus metrics server
    start_http_server(8000)
    print("Prometheus metrics server started on port 8000")
    
    # Load the ML model
    model = load_model()
    print("ML model loaded successfully")
    
    # Set initial algorithm
    update_nginx_config(0)  # Start with round-robin
    
    # Main loop
    while True:
        try:
            # Get metrics
            metrics = get_metrics()
            
            # Predict the best algorithm
            algorithm_id = model.predict(metrics)[0]
            
            # Update Nginx config
            update_nginx_config(algorithm_id)
            
            # Wait for 5 seconds
            time.sleep(5)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()