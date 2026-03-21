import React, { useState, useEffect, useCallback } from 'react';
import { getBaseUrl } from '../utils/config';

export default function HeatmapOverlay({ serverIP }) {
  const [points, setPoints] = useState([]);
  const baseUrl = getBaseUrl(serverIP);

  const fetchHeatmapData = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/api/heatmap/3d?hours=2&grid=32`);
      if (response.ok) {
        const data = await response.json();
        setPoints(data.points || []);
      }
    } catch (err) {
      console.error('Heatmap fetch error:', err);
    }
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(fetchHeatmapData, 0);
    const interval = setInterval(fetchHeatmapData, 5000);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(interval);
    };
  }, [fetchHeatmapData]);

  if (points.length === 0) return null;

  return (
    <div className="absolute inset-0 z-10 pointer-events-none" style={{ mixBlendMode: 'screen' }}>
      {points.map((pt, i) => {
        const intensity = pt.heat_intensity || 0;
        if (intensity < 0.05) return null;

        // Define color based on intensity (blue for low, red for high)
        const isHot = intensity > 0.5;
        const colorStops = isHot
          ? `rgba(255, 0, 0, ${intensity * 0.7}) 0%, rgba(255, 0, 0, 0) 70%`
          : `rgba(0, 100, 255, ${intensity * 0.7}) 0%, rgba(0, 100, 255, 0) 70%`;

        const size = 15 + (intensity * 25);

        return (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              left: `${pt.x * 100}%`,
              top: `${pt.y * 100}%`,
              width: `${size}%`,
              height: `${size}%`,
              transform: 'translate(-50%, -50%)',
              background: `radial-gradient(circle, ${colorStops})`,
              filter: 'blur(8px)',
            }}
          />
        );
      })}
    </div>
  );
}
