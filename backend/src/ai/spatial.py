import numpy as np

try:
    from sklearn.cluster import DBSCAN
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

def detect_huddling(bird_track_points, eps_pixels=80, min_birds_per_cluster=8):
    """
    Analisa coordenadas X,Y das aves nos ultimos minutos.
    Usa o algoritmo DBSCAN (Machine Learning Espacial / Clustering de Densidade) 
    para identificar se as aves estao se amontoando intensamente, 
    o que na avicultura é um sinal critico de estresse termico (frio ou corrente de ar).
    
    bird_track_points: Lista de dicts [{"x": 100, "y": 200}, ...]
    eps_pixels: Raio de busca para agrupar aves.
    min_birds_per_cluster: Quantidade minima de aves coladas para formar um 'amontoado'.
    """
    if not _SKLEARN_AVAILABLE:
        return {"error": "scikit-learn is not installed."}
        
    if len(bird_track_points) < min_birds_per_cluster:
        return {
            "huddling_detected": False,
            "clusters_found": 0,
            "msg": "Nao ha aves suficientes rastreadas para analise espacial."
        }
        
    # Extrair matriz de coordenadas bidimensionais
    X = np.array([[pt["x"], pt["y"]] for pt in bird_track_points])
    
    # Processar IA Espacial (DBSCAN)
    db = DBSCAN(eps=eps_pixels, min_samples=min_birds_per_cluster)
    labels = db.fit_predict(X)
    
    # labels == -1 significa 'ruido' (ou seja, aves confortaveis e bem espalhadas)
    # labels >= 0 representam aves densamente aglomeradas
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    
    if n_clusters == 0:
        return {
            "huddling_detected": False,
            "clusters_found": 0,
            "density_score": 0.0,
            "msg": "As aves estao bem distribuidas pelo galpao (Excelente Conforto Termico)."
        }
        
    # Contar proporcao do lote que esta amontoado
    birds_in_clusters = sum(1 for label in labels if label != -1)
    percentage_huddling = birds_in_clusters / len(bird_track_points)
    
    # Regra de negocio: Se mais de 25% das aves detectadas na tela estao em amontoados apertados, eh um risco!
    is_critical = percentage_huddling > 0.25
    
    # Calcular o Centroide (x, y) de cada amontoado para que o Frontend possa desenhar o alerta na camera de video
    cluster_centers = []
    for i in range(n_clusters):
        cluster_points = X[labels == i]
        cx = int(np.mean(cluster_points[:, 0]))
        cy = int(np.mean(cluster_points[:, 1]))
        cluster_centers.append({"x": cx, "y": cy, "bird_count": len(cluster_points)})
    
    return {
        "huddling_detected": is_critical,
        "clusters_found": n_clusters,
        "density_score": round(percentage_huddling * 100, 2), # % de aves sofrendo de frio
        "cluster_centers": cluster_centers,
        "msg": "ALERTA VERMELHO: Amontoamento termico severo! As aves estao aglomeradas." if is_critical else "Pequenos grupos isolados."
    }
