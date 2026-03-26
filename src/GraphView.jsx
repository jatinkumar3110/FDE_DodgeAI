import React, { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

function GraphView({ apiUrl }) {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    const loadGraph = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(apiUrl, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Graph request failed (${response.status})`);
        }

        const payload = await response.json();
        setData({
          nodes: Array.isArray(payload?.nodes) ? payload.nodes : [],
          links: Array.isArray(payload?.links) ? payload.links : [],
        });
      } catch (err) {
        if (err.name !== "AbortError") {
          console.error("Graph fetch error:", err);
          setError("Graph not available");
          setData({ nodes: [], links: [] });
        }
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
    return () => controller.abort();
  }, [apiUrl]);

  const safeGraph = useMemo(() => {
    return {
      nodes: data.nodes.map((n, i) => ({
        id: String(n?.id || i),
        label: String(n?.label || n?.id || i),
      })),
      links: data.links
        .filter((l) => l && l.source !== undefined && l.target !== undefined)
        .map((l) => ({
          source: String(l.source),
          target: String(l.target),
        })),
    };
  }, [data]);

  if (loading) {
    return (
      <section className="graph-shell">
        <div className="graph-state">Loading graph...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="graph-shell">
        <div className="graph-state">{error}</div>
      </section>
    );
  }

  if (!safeGraph.nodes.length) {
    return (
      <section className="graph-shell">
        <div className="graph-state">No graph data</div>
      </section>
    );
  }

  try {
    return (
      <section className="graph-shell">
        <ForceGraph2D graphData={safeGraph} nodeLabel="label" />
      </section>
    );
  } catch (e) {
    console.error("Graph render error:", e);
    return (
      <section className="graph-shell">
        <div className="graph-state">Graph failed</div>
      </section>
    );
  }
}

export default GraphView;
