import pytest
import time
from src.vision.tri_zone_analyzer import TriZoneBehaviorAnalyzer

def test_tri_zone_behavior_analyzer():
    analyzer = TriZoneBehaviorAnalyzer(window_size=3)

    # Test 1: Empty birds
    result = analyzer.analyze_zones([], 100, 100, timestamp=time.time())
    assert result['drinker_count'] == 0
    assert result['brooder_count'] == 0
    assert result['feeder_count'] == 0
    assert result['welfare_status'] == 'CONFORTO_IDEAL'
    assert result['welfare_index'] == 0.95

    # Test 2: Birds in all zones (Comfort)
    birds = [(10, 50), (50, 50), (90, 50)]  # Drinker (0.1), Brooder (0.5), Feeder (0.9)
    result = analyzer.analyze_zones(birds, 100, 100, timestamp=time.time())
    assert result['drinker_count'] == 1
    assert result['brooder_count'] == 1
    assert result['feeder_count'] == 1
    assert result['welfare_status'] == 'CONFORTO_IDEAL'
    assert result['welfare_index'] == 0.95

    # Test 3: Cold Stress (Brooder > 60%)
    birds = [(50, 50), (55, 50), (60, 50), (10, 50)]
    result = analyzer.analyze_zones(birds, 100, 100, timestamp=time.time())
    assert result['brooder_count'] == 3
    assert result['welfare_status'] == 'ESTRESSE_FRIO'
    assert result['welfare_index'] == 0.25 # 1.0 - 0.75

    # Test 4: Heat Stress (Drinker > 50%)
    birds = [(10, 50), (20, 50), (30, 50), (90, 50)]
    result = analyzer.analyze_zones(birds, 100, 100, timestamp=time.time())
    assert result['drinker_count'] == 3
    assert result['welfare_status'] == 'ESTRESSE_CALOR'
    assert result['welfare_index'] == 0.25 # 1.0 - 0.75

    # Check if window_size rolling works properly
    assert len(analyzer._stay_history) == 3

    # Test summary
    summary = analyzer.get_stay_frequency_summary()
    assert summary['total_samples'] == 3 # Because of window_size=3

    # Test get_stay_frequency_summary with empty history
    empty_analyzer = TriZoneBehaviorAnalyzer()
    summary = empty_analyzer.get_stay_frequency_summary()
    assert summary['total_samples'] == 0
    assert summary['avg_welfare_index'] == 1.0
