import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os

DATASET_PATH = "dataset.csv"
MODEL_DIR = "meta-lb/models"
MODEL_PATH = os.path.join(MODEL_DIR, "lb_model.pkl")

def main():
    print(f"Loading dataset from {DATASET_PATH}...")
    try:
        data = pd.read_csv(DATASET_PATH)
    except FileNotFoundError:
        print(f"Error: Dataset file {DATASET_PATH} not found. Please run generate_dataset.py first.")
        return

    if data.empty:
        print("Dataset is empty. No model will be trained.")
        return

    print("Dataset loaded successfully:")
    print(data.head())
    print(f"\nDataset shape: {data.shape}")
    print(f"\nLabel distribution:\n{data['label'].value_counts()}")

    X = data[['cpu', 'mem', 'latency', 'p95', 'throughput', 'connections']]
    y = data['label']

    print("\nSplitting data into training and testing sets (80/20 stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f"Training set shape: X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"Test set shape: X_test: {X_test.shape}, y_test: {y_test.shape}")

    param_grid = {
        'n_estimators': [50, 100],
        'max_depth': [None, 10, 20],
        # Add other parameters here if needed, e.g., 'min_samples_split', 'min_samples_leaf'
    }

    print("\nStarting GridSearchCV for RandomForestClassifier...")
    # RandomForestClassifier with class_weight='balanced' can be helpful if classes are imbalanced
    rf = RandomForestClassifier(random_state=42, class_weight='balanced') 
    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=5, scoring='accuracy', n_jobs=-1, verbose=1)
    
    grid_search.fit(X_train, y_train)

    print("\nGridSearchCV complete.")
    print(f"Best parameters found: {grid_search.best_params_}")
    print(f"Best cross-validation accuracy: {grid_search.best_score_:.4f}")

    best_model = grid_search.best_estimator_

    print("\nEvaluating model on the test set...")
    y_pred = best_model.predict(X_test)

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Ensure the model directory exists
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"Created directory: {MODEL_DIR}")

    print(f"\nSaving the best model to {MODEL_PATH}...")
    joblib.dump(best_model, MODEL_PATH)
    print("Model saved successfully.")

if __name__ == "__main__":
    main()