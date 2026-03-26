import React, { useEffect, useMemo, useRef, useState } from "react";
import { ForceGraph2D } from "react-force-graph";

const TYPE_COLORS = {
  Order: "#1d4ed8",
  OrderItem: "#2563eb",
  Delivery: "#0f766e",
  DeliveryItem: "#0d9488",
  Invoice: "#b45309",
  InvoiceItem: "#d97706",
  JournalEntry: "#7c3aed",
  Payment: "#db2777",
  Customer: "#059669",
  Product: "#dc2626",
  Plant: "#4f46e5",
  unknown: "#64748b",
};

function GraphView({ apiUrl, highlightedNodeIds = [] }) {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [size, setSize] = useState({ width: 600, height: 420 });

  const containerRef = useRef(null);

  useEffect(() => {
    const resize = () => {
      if (!containerRef.current) {
        return;
      }
      const { clientWidth, clientHeight } = containerRef.current;
      setSize({
        width: Math.max(clientWidth, 320),
        height: Math.max(clientHeight, 280),
      });
    };

    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    const loadGraph = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(apiUrl, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Unable to load graph (${response.status})`);
        }

        const payload = await response.json();
        setGraphData({
          nodes: payload?.nodes || [],
          links: payload?.links || [],
        });
      } catch (loadError) {
        if (loadError.name !== "AbortError") {
          setError("Graph is unavailable");
        }
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
    return () => controller.abort();
  }, [apiUrl]);

  const safeGraphData = useMemo(() => {
    const nodes = Array.isArray(graphData?.nodes)
      ? graphData.nodes
          .filter((node) => node && node.id !== undefined && node.id !== null)
          .map((node) => ({
            id: String(node.id),
            label: node.label || String(node.id),
            type: node.type || "unknown",
          }))
      : [];

    const links = Array.isArray(graphData?.links)
      ? graphData.links
          .filter((link) => link && link.source !== undefined && link.target !== undefined)
          .map((link) => ({
            source: String(link.source),
            target: String(link.target),
          }))
      : [];

    return { nodes, links };
  }, [graphData]);

  const highlightSet = useMemo(() => new Set((highlightedNodeIds || []).map(String)), [highlightedNodeIds]);

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
        <div className="graph-state error">{error}</div>
      </section>
    );
  }

  if (!safeGraphData.nodes.length) {
    return (
      <section className="graph-shell">
        <div className="graph-state">No graph data</div>
      </section>
    );
  }

  try {
    return (
      <section className="graph-shell">
        <div className="graph-header">
          <h2>O2C Graph</h2>
          <span>
            Nodes {safeGraphData.nodes.length} | Links {safeGraphData.links.length}
          </span>
        </div>

        <div className="graph-canvas" ref={containerRef}>
          <ForceGraph2D
            width={size.width}
            height={size.height}
            graphData={safeGraphData}
            nodeLabel="label"
            nodeColor={(node) => {
              const base = TYPE_COLORS[node.type] || TYPE_COLORS.unknown;
              if (highlightSet.size === 0) {
                return base;
              }
              return highlightSet.has(String(node.id)) ? base : "#cbd5e1";
            }}
            linkColor={(link) => {
              if (highlightSet.size === 0) {
                return "#d1d5db";
              }
              const sourceId = String(link.source?.id ?? link.source);
              const targetId = String(link.target?.id ?? link.target);
              return highlightSet.has(sourceId) && highlightSet.has(targetId) ? "#1d4ed8" : "#d1d5db";
            }}
            linkWidth={(link) => {
              if (highlightSet.size === 0) {
                return 1;
              }
              const sourceId = String(link.source?.id ?? link.source);
              const targetId = String(link.target?.id ?? link.target);
              return highlightSet.has(sourceId) && highlightSet.has(targetId) ? 2.2 : 0.8;
            }}
            cooldownTicks={80}
            enablePanInteraction
            enableZoomInteraction
          />
        </div>
      </section>
    );
  } catch (e) {
    console.error("Graph render error:", e);
    return (
      <section className="graph-shell">
        <div className="graph-state error">Graph failed</div>
      </section>
    );
  }
}

export default GraphView;
