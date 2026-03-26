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
  Unknown: "#64748b",
};

const getNodeId = (nodeOrId) =>
  typeof nodeOrId === "object" && nodeOrId !== null ? nodeOrId.id : nodeOrId;

function GraphView({ apiUrl, highlightedNodeIds = [] }) {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [searchText, setSearchText] = useState("");
  const [size, setSize] = useState({ width: 600, height: 400 });

  const containerRef = useRef(null);
  const graphRef = useRef(null);

  useEffect(() => {
    const resize = () => {
      if (!containerRef.current) {
        return;
      }
      const { clientWidth, clientHeight } = containerRef.current;
      setSize({
        width: Math.max(clientWidth, 300),
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
          throw new Error("Unable to load graph");
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

  const activeNode = hoveredNode || selectedNode;
  const resultHighlightSet = useMemo(() => new Set(highlightedNodeIds || []), [highlightedNodeIds]);

  const adjacency = useMemo(() => {
    const nextNodes = new Set();
    const nextLinks = new Set();

    if (!activeNode) {
      return { nodes: nextNodes, links: nextLinks };
    }

    const activeNodeId = getNodeId(activeNode);
    nextNodes.add(activeNodeId);

    graphData.links.forEach((link) => {
      const sourceId = getNodeId(link.source);
      const targetId = getNodeId(link.target);

      if (sourceId === activeNodeId || targetId === activeNodeId) {
        nextLinks.add(link);
        nextNodes.add(sourceId);
        nextNodes.add(targetId);
      }
    });

    return { nodes: nextNodes, links: nextLinks };
  }, [activeNode, graphData.links]);

  const queryLinks = useMemo(() => {
    const links = new Set();
    if (resultHighlightSet.size === 0) {
      return links;
    }

    graphData.links.forEach((link) => {
      const sourceId = getNodeId(link.source);
      const targetId = getNodeId(link.target);
      if (resultHighlightSet.has(sourceId) && resultHighlightSet.has(targetId)) {
        links.add(link);
      }
    });

    return links;
  }, [graphData.links, resultHighlightSet]);

  const mergedHighlightNodes = useMemo(() => {
    const output = new Set();
    resultHighlightSet.forEach((id) => output.add(id));
    adjacency.nodes.forEach((id) => output.add(id));
    return output;
  }, [resultHighlightSet, adjacency.nodes]);

  const mergedHighlightLinks = useMemo(() => {
    const output = new Set();
    queryLinks.forEach((link) => output.add(link));
    adjacency.links.forEach((link) => output.add(link));
    return output;
  }, [adjacency.links, queryLinks]);

  const shouldFade = resultHighlightSet.size > 0;

  const handleNodeSearch = () => {
    const query = searchText.trim().toLowerCase();
    if (!query) {
      return;
    }

    const match = graphData.nodes.find((node) => {
      const id = String(node.id || "").toLowerCase();
      const label = String(node.label || "").toLowerCase();
      const type = String(node.type || "").toLowerCase();
      return id.includes(query) || label.includes(query) || type.includes(query);
    });

    if (!match) {
      return;
    }

    setSelectedNode(match);

    if (graphRef.current && typeof match.x === "number" && typeof match.y === "number") {
      graphRef.current.centerAt(match.x, match.y, 700);
      graphRef.current.zoom(4, 700);
    }
  };

  const selectedNodeData = selectedNode || null;

  return (
    <section className="graph-shell">
      <div className="graph-header">
        <h2>O2C Graph</h2>
        <span>
          Nodes {graphData.nodes.length} | Links {graphData.links.length}
        </span>
      </div>

      <div className="graph-toolbar">
        <input
          type="text"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="Search node by id, label, or type"
        />
        <button type="button" onClick={handleNodeSearch}>
          Find Node
        </button>
      </div>

      <div className="graph-canvas" ref={containerRef}>
        {loading ? <div className="graph-state">Loading graph...</div> : null}
        {!loading && error ? <div className="graph-state error">{error}</div> : null}

        {!loading && !error ? (
          <ForceGraph2D
            ref={graphRef}
            width={size.width}
            height={size.height}
            graphData={graphData}
            nodeLabel={(node) => `${node.type}: ${node.label}`}
            nodeColor={(node) => {
              const nodeId = node.id;
              const baseColor = TYPE_COLORS[node.type] || TYPE_COLORS.Unknown;
              const isHighlighted = mergedHighlightNodes.has(nodeId);

              if (!shouldFade) {
                return isHighlighted || mergedHighlightNodes.size === 0 ? baseColor : "#cbd5e1";
              }

              if (isHighlighted) {
                return baseColor;
              }

              return "#e2e8f0";
            }}
            nodeRelSize={5}
            linkWidth={(link) => (mergedHighlightLinks.has(link) ? 2.8 : 1)}
            linkColor={(link) => (mergedHighlightLinks.has(link) ? "#1d4ed8" : "#d1d5db")}
            onNodeHover={setHoveredNode}
            onNodeClick={setSelectedNode}
            cooldownTicks={80}
            enablePanInteraction
            enableZoomInteraction
          />
        ) : null}
      </div>

      <div className="graph-meta">
        <h3>Node Metadata</h3>
        {!selectedNodeData ? (
          <p>Click a node to inspect it.</p>
        ) : (
          <pre>{JSON.stringify(selectedNodeData, null, 2)}</pre>
        )}
      </div>
    </section>
  );
}

export default GraphView;
