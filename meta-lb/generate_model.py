import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

# Generate a simple model for demonstration purposes
def generate_model():
    # Create a simple dataset
    X = np.random.rand(100, 4)  # 4 features: CPU, Memory, Latency, Throughput
    
    # Create labels (0: round-robin, 1: least_conn, 2: ip_hash)
    y = np.zeros(100, dtype=int)
    
    # Assign labels based on some rules
    for i in range(100):
        if X[i, 0] > 0.7:  # High CPU
            y[i] = 1  # least_conn
        elif X[i, 2] > 0.8:  # High Latency
            y[i] = 2  # ip_hash
        else:
            y[i] = 0  # round-robin
    
    # Train a Random Forest model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    
    # Save the model
    joblib.dump(model, 'lb_model.pkl')
    print("Model generated and saved as lb_model.pkl")

if __name__ == "__main__":
    generate_model()