import { useState } from "react";
import type { SpatialAnalysis } from "./types";

export function SpatialMetrics({ analysis }: { analysis?: SpatialAnalysis | null }) {
  const [active, setActive] = useState(0);
  const [cell, setCell] = useState<number | null>(null);
  const [overlay, setOverlay] = useState(true);
  if (!analysis) return <section className="spatial-section"><h3>Regional measurements unavailable</h3><p>Restart the updated backend and check this file again to calculate the new metrics.</p></section>;
  if (analysis.status !== "complete" || !analysis.metrics.length) return <section className="spatial-section"><h3>Regional measurements did not run</h3><p>{analysis.message}</p></section>;
  const metric = analysis.metrics[active] ?? analysis.metrics[0];
  const spread = metric.maximum - metric.minimum;
  const selected = cell === null ? null : metric.cells[cell];
  return <section className="spatial-section" aria-label="Image measurements">
    <div className="spatial-heading"><div><span className="result-label">MEASUREMENTS FROM THIS IMAGE</span><h2>Look closer, region by region.</h2></div><p>Choose a measurement, then select a square to inspect its value. Brighter map cells mean a higher measurement—not a greater chance of fakery.</p></div>
    <div className="metric-tabs" role="group" aria-label="Choose measurement">
      {analysis.metrics.map((item, index) => <button key={item.id} type="button" aria-pressed={active === index} onClick={() => {setActive(index); setCell(null);}}>
        <span>{item.name}</span><strong>{item.value.toFixed(2)} <small>{item.unit}</small></strong><em>{item.value_label}</em>
      </button>)}
    </div>
    <div className="spatial-body">
      <div className="measurement-figure">
        <div className="map-controls"><strong>{metric.name}</strong><label><input type="checkbox" checked={overlay} onChange={event => setOverlay(event.target.checked)} /> Show map</label></div>
        <div className="measurement-image" style={{aspectRatio:`${analysis.width}/${analysis.height}`}}>
          {analysis.preview_data_url && <img src={analysis.preview_data_url} alt="Oriented analysis image with regional measurement overlay" />}
          <div className="measurement-grid" style={{gridTemplateColumns:`repeat(${analysis.columns}, 1fr)`, gridTemplateRows:`repeat(${analysis.rows}, 1fr)`}}>
            {metric.cells.map((value, index) => {
              const relative = spread > 0.0001 ? (value - metric.minimum) / spread : 0;
              const label = `Row ${Math.floor(index / analysis.columns) + 1}, column ${index % analysis.columns + 1}: ${value.toFixed(2)} ${metric.unit}`;
              return <button key={index} type="button" title={label} aria-label={label} aria-pressed={cell === index} onClick={() => setCell(index)} style={{background:overlay ? `rgba(255, 161, 43, ${.06 + .64 * relative})` : "transparent"}} />;
            })}
          </div>
        </div>
        <div className="map-legend"><span>{metric.minimum.toFixed(2)}</span><i /><span>{metric.maximum.toFixed(2)} {metric.unit}</span></div>
        <small>Scale is relative to this image. Coordinates run from the top left.</small>
      </div>
      <div className="measurement-notes">
        <span className="result-label">WHAT WAS MEASURED</span><h3>{metric.name}</h3><p>{metric.summary}</p>
        <div className="region-reading" aria-live="polite"><strong>{cell === null ? "Select a region on the map" : `Row ${Math.floor(cell / analysis.columns) + 1} · Column ${cell % analysis.columns + 1}`}</strong><p>{selected === null ? "Each square represents a measured part of your image." : `${selected.toFixed(2)} ${metric.unit} · ${Math.abs(selected - metric.median).toFixed(2)} ${metric.unit} ${selected >= metric.median ? "above" : "below"} the median region.`}</p></div>
        <h4>What can explain it</h4><p>{metric.limitation}</p>
        <details><summary>Calculation and analysis resolution</summary><p>{metric.method}</p><p>{analysis.message}</p></details>
      </div>
    </div>
    <p className="spatial-scope">These are measured image properties, not a tampering score. Light-source direction, shadow geometry, and face-swap localization have not been tested.</p>
  </section>;
}
