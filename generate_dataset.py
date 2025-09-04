import os
import time
import csv
import subprocess
import requests
from prometheus_api_client import PrometheusConnect

PROMETHEUS_URL = "http://prometheus:9090"
LB_ALGORITHMS = {
    "round-robin": {"config": "server svc1:80;\nserver svc2:80;\nserver svc3:80;", "label": 0},
    "least_conn": {"config": "least_conn;\nserver svc1:80;\nserver svc2:80;\nserver svc3:80;", "label": 1},
    "ip_hash": {"config": "ip_hash;\nserver svc1:80;\nserver svc2:80;\nserver svc3:80;", "label": 2}
}
ALGO_CONF_PATH = "lb-conf/algo.conf"
DATASET_PATH = "dataset.csv"

# Traffic Scenarios for Locust
# These would typically be different locustfiles or configurations passed to locust
# For simplicity, we'll use the same locustfile but simulate different durations/patterns conceptually
SCENARIOS = {
    "ramp": {"duration": "2m", "users": 100, "spawn_rate": 10, "description": "Ramping up users"},
    "spike": {"duration": "1m", "users": 500, "spawn_rate": 100, "description": "Sudden spike in users"},
    "steady_high": {"duration": "3m", "users": 200, "spawn_rate": 20, "description": "Sustained high traffic"},
    "steady_low": {"duration": "4m", "users": 50, "spawn_rate": 5, "description": "Sustained low traffic"}
}

DATA_COLLECTION_WINDOW_SECONDS = 10

prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

def run_locust(scenario_config):
    print(f"Starting Locust for scenario: {scenario_config['description']} for {scenario_config['duration']}")
    # In a real scenario, you might pass different locustfiles or parameters
    # For this example, we assume locustfile.py in locust/ handles the load pattern
    # and we control duration and user load via command line arguments.
    # The command needs to be run in the background.
    # Note: Adjust users and spawn-rate as needed for your environment.
    locust_cmd = [
        "locust",
        "-f", "locust/locustfile.py",
        "--headless",
        "-u", str(scenario_config['users']),
        "-r", str(scenario_config['spawn_rate']),
        "--run-time", scenario_config['duration'],
        "--host=http://nginx"
    ]
    process = subprocess.Popen(locust_cmd)
    print(f"Locust process started with PID: {process.pid}")
    return process

def update_nginx_config(algo_name):
    print(f"Updating Nginx config for {algo_name}")
    with open(ALGO_CONF_PATH, "w") as f:
        f.write(LB_ALGORITHMS[algo_name]["config"])
    
    # Reload Nginx
    # Ensure DOCKER_HOST is set if running this script outside a container that can reach Docker daemon
    # Or that the script runs in a container with Docker socket mounted
    try:
        # Using the specific container name from docker-compose.yml
        subprocess.run(["docker", "exec", "meta-load-balancer_nginx_1", "nginx", "-s", "reload"], check=True)
        print("Nginx reloaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error reloading Nginx: {e}")
        # Potentially exit or handle error if Nginx reload is critical
    except FileNotFoundError:
        print("Error: 'docker' command not found. Make sure Docker is installed and in PATH, or this script is run in an environment with access to Docker.")
        # Potentially exit

def fetch_metrics():
    print(f"Waiting {DATA_COLLECTION_WINDOW_SECONDS}s for metrics to stabilize...")
    time.sleep(DATA_COLLECTION_WINDOW_SECONDS)
    print("Fetching metrics from Prometheus...")
    metrics = {}
    try:
        # CPU Usage (node_exporter) - average over last window
        # Note: Query might need adjustment based on your exact node_exporter setup and labels
        # This query calculates the average CPU usage percentage over the last DATA_COLLECTION_WINDOW_SECONDS.
        # It assumes 'instance' and 'job' labels are present. Adjust if your labels differ.
        # It calculates (1 - idle_cpu) * 100.
        cpu_query = f'avg_over_time(100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{{mode="idle"}}[1m]))))[{DATA_COLLECTION_WINDOW_SECONDS}s:1s]'
        cpu_data = prom.custom_query(query=cpu_query)
        if cpu_data and cpu_data[0]:
            metrics['cpu_usage'] = round(float(cpu_data[0]['value'][1]), 2) # value is [timestamp, value]
        else:
            metrics['cpu_usage'] = 0 # Default if no data

        # Memory Usage (node_exporter) - average over last window
        # This query calculates memory usage percentage: (1 - (available_memory / total_memory)) * 100
        mem_query = f'avg_over_time(100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)))[{DATA_COLLECTION_WINDOW_SECONDS}s:1s]'
        mem_data = prom.custom_query(query=mem_query)
        if mem_data and mem_data[0]:
            metrics['mem_usage'] = round(float(mem_data[0]['value'][1]), 2)
        else:
            metrics['mem_usage'] = 0

        # Latency & Throughput (from meta-lb, assuming it exposes these via Prometheus)
        # These queries depend on how meta-lb exposes metrics. Placeholder queries:
        # Assuming nginx_http_request_duration_seconds_bucket from nginx-prometheus-exporter or similar for latency
        # For Nginx, latency is often a histogram. We'll query for p95.
        # This query assumes you have nginx-prometheus-exporter set up and metrics are available.
        # The 'le' label is part of histogram buckets.
        avg_latency_query = f'avg_over_time(histogram_quantile(0.50, sum(rate(nginx_http_request_duration_seconds_bucket[1m])) by (le, job))[{DATA_COLLECTION_WINDOW_SECONDS}s:1s]) * 1000' # ms
        p95_latency_query = f'avg_over_time(histogram_quantile(0.95, sum(rate(nginx_http_request_duration_seconds_bucket[1m])) by (le, job))[{DATA_COLLECTION_WINDOW_SECONDS}s:1s]) * 1000' # ms
        
        # Throughput: requests per second from Nginx exporter
        throughput_query = f'avg_over_time(sum(rate(nginx_http_requests_total[1m])) by (job))[{DATA_COLLECTION_WINDOW_SECONDS}s:1s]'
        
        # Active connections from Nginx exporter
        active_connections_query = f'avg_over_time(nginx_http_connections_active[{DATA_COLLECTION_WINDOW_SECONDS}s:1s])'

        avg_latency_data = prom.custom_query(query=avg_latency_query)
        p95_latency_data = prom.custom_query(query=p95_latency_query)
        throughput_data = prom.custom_query(query=throughput_query)
        active_connections_data = prom.custom_query(query=active_connections_query)

        metrics['avg_latency'] = round(float(avg_latency_data[0]['value'][1]), 2) if avg_latency_data and avg_latency_data[0] else 0
        metrics['p95_latency'] = round(float(p95_latency_data[0]['value'][1]), 2) if p95_latency_data and p95_latency_data[0] else 0
        metrics['throughput'] = round(float(throughput_data[0]['value'][1]), 2) if throughput_data and throughput_data[0] else 0
        metrics['active_connections'] = round(float(active_connections_data[0]['value'][1]), 0) if active_connections_data and active_connections_data[0] else 0
        
    except requests.exceptions.ConnectionError:
        print(f"Error connecting to Prometheus at {PROMETHEUS_URL}. Is it running and accessible?")
        return None # Indicate failure
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        # Set defaults if specific metrics fail
        metrics.setdefault('cpu_usage', 0)
        metrics.setdefault('mem_usage', 0)
        metrics.setdefault('avg_latency', 9999) # High latency for failed fetch
        metrics.setdefault('p95_latency', 9999)
        metrics.setdefault('throughput', 0)
        metrics.setdefault('active_connections', 0)

    print(f"Collected metrics: {metrics}")
    return metrics

def main():
    # Check if dataset file exists, if not, write header
    file_exists = os.path.isfile(DATASET_PATH)
    with open(DATASET_PATH, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["cpu", "mem", "latency", "p95", "throughput", "connections", "label"])

        for scenario_name, scenario_config in SCENARIOS.items():
            print(f"\n--- Running Scenario: {scenario_name} ({scenario_config['description']}) ---")
            locust_process = run_locust(scenario_config)
            
            # Wait for locust to run for its duration. 
            # This is a simplification. In reality, you'd monitor the locust process.
            # For headless mode, locust runs for the specified --run-time then exits.
            locust_process.wait() # Wait for locust to finish its run
            print(f"Locust finished for scenario: {scenario_name}")

            scenario_results = []
            for algo_name in LB_ALGORITHMS.keys():
                update_nginx_config(algo_name)
                # Allow Nginx and system to stabilize after config change
                print(f"Waiting a bit after Nginx reload for {algo_name}...")
                time.sleep(5) # Short wait after reload
                
                current_metrics = fetch_metrics()
                if current_metrics:
                    scenario_results.append({
                        "algo_name": algo_name,
                        "metrics": current_metrics,
                        "label": LB_ALGORITHMS[algo_name]["label"]
                    })
                else:
                    print(f"Skipping {algo_name} due to metric fetch error.")
            
            if not scenario_results:
                print(f"No results collected for scenario {scenario_name}. Skipping.")
                continue

            # Determine best algorithm for this scenario based on avg_latency
            best_result = min(scenario_results, key=lambda x: x['metrics']['avg_latency'])
            best_algo_label = best_result['label']
            print(f"Best algorithm for scenario '{scenario_name}': {best_result['algo_name']} (Label: {best_algo_label}) with avg_latency: {best_result['metrics']['avg_latency']}")

            # For simplicity, we use the metrics from the 'best_result' run as the features for this scenario.
            # A more sophisticated approach might average metrics across the scenario or use metrics leading up to the decision.
            features = best_result['metrics'] # Using metrics of the best performing algo for this scenario
            
            writer.writerow([
                features['cpu_usage'],
                features['mem_usage'],
                features['avg_latency'],
                features['p95_latency'],
                features['throughput'],
                features['active_connections'],
                best_algo_label
            ])
            csvfile.flush() # Ensure data is written to disk
            print(f"Appended data for scenario '{scenario_name}' with label '{best_algo_label}' to {DATASET_PATH}")

    print("\nDataset generation complete.")

if __name__ == "__main__":
    # Small delay to allow other services (like Prometheus) to be fully up if run via docker-compose run
    print("Starting dataset generation script. Waiting 15s for services to initialize...")
    time.sleep(15) 
    main()