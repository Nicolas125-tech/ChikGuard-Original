import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

def detect_multivariate_anomaly(sensor_history, current_state):
    """
    Detector de anomalias usando Isolation Forest.
    sensor_history: list of dicts [{"temp": 28, "hum": 60, "amm": 15, "cough": 10}, ...]
    current_state: dict {"temp": 28, "hum": 60, "amm": 15, "cough": 10}
    """
    if not _SKLEARN_AVAILABLE:
        return {"error": "scikit-learn is not installed in the environment."}
        
    if len(sensor_history) < 20:
        return {"error": "Insufficient historical data for Isolation Forest. Need at least 20 points."}
        
    features = ["temp", "hum", "amm", "cough"]
    
    # Preparar matriz de treino (baseline comportamental)
    X_train = []
    for item in sensor_history:
        X_train.append([float(item.get(f, 0.0)) for f in features])
        
    X_train = np.array(X_train)
    
    # Ponto atual a ser testado
    X_current = np.array([[float(current_state.get(f, 0.0)) for f in features]])
    
    # Isolation Forest: assume ~5% de contaminação natural no histórico
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X_train)
    
    # Avaliação: score < 0 = Anomalia, prediction = -1 (Anomalia) ou 1 (Normal)
    score = float(model.decision_function(X_current)[0])
    prediction = int(model.predict(X_current)[0])
    is_anomaly = prediction == -1
    
    # Se for anomalia, calcular Z-scores para identificar os culpados
    contributions = {}
    if is_anomaly:
        means = np.mean(X_train, axis=0)
        stds = np.std(X_train, axis=0) + 1e-6
        z_scores = (X_current[0] - means) / stds
        
        for i, f in enumerate(features):
            # Apenas desvios significativos
            if abs(z_scores[i]) > 1.5:
                contributions[f] = round(float(z_scores[i]), 2)
            
    return {
        "is_anomaly": is_anomaly,
        "score": round(score, 4),
        "confidence": round(abs(score) * 100, 2),
        "contributions": contributions
    }
