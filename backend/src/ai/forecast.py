from datetime import timedelta

import numpy as np


def predict_slaughter_date(weight_data, start_date, target_weight=2800.0):
    """
    weight_data: List of dicts [{"day": int, "avg_weight": float}, ...]
    start_date: datetime object of the batch start date
    target_weight: target weight in grams

    Returns a dict with {"target_date": "YYYY-MM-DD", "target_day": int, "projections": [...]}
    """
    # Exigir pelo menos 3 dias de dados para regressão polinomial estável
    if len(weight_data) < 3:
        return None

    weight_data = sorted(weight_data, key=lambda x: x["day"])

    x = np.array([d["day"] for d in weight_data])
    y = np.array([d["avg_weight"] for d in weight_data])

    # Modelo preditivo: Regressão Polinomial de Grau 2
    # Modela o ganho de peso (curva S inicial/intermediária) de forma leve e rápida
    coeffs = np.polyfit(x, y, 2)
    poly = np.poly1d(coeffs)

    current_day = int(np.max(x))
    future_day = current_day

    projections = []

    # Projetar até o final de um ciclo longo (90 dias)
    while future_day < 90:
        future_day += 1
        pred_w = float(poly(future_day))

        projections.append(
            {
                "day": future_day,
                "estimated_weight_g": max(0, round(pred_w, 2)),
                "date": (start_date + timedelta(days=future_day)).strftime("%Y-%m-%d"),
            }
        )

        # Alvo atingido!
        if pred_w >= target_weight:
            return {
                "target_date": (start_date + timedelta(days=future_day)).strftime("%Y-%m-%d"),
                "target_day": future_day,
                "target_weight": target_weight,
                "equation_coeffs": [float(c) for c in coeffs],
                "projections": projections,
            }

    # Se não atingir em 90 dias
    return {
        "target_date": None,
        "target_day": None,
        "target_weight": target_weight,
        "equation_coeffs": [float(c) for c in coeffs],
        "projections": projections,
    }
