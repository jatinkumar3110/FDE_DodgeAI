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
  const [focusNodeId, setFocusNodeId] = useState(null);
  const [searchMatchNodeId, setSearchMatchNodeId] = useState(null);
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

  const focusNeighborhood = useMemo(() => {
    const nodes = new Set();
    const links = new Set();

    if (!focusNodeId) {
      return { nodes, links };
    }

    nodes.add(focusNodeId);
    graphData.links.forEach((link) => {
      const sourceId = getNodeId(link.source);
      const targetId = getNodeId(link.target);
      if (sourceId === focusNodeId || targetId === focusNodeId) {
        nodes.add(sourceId);
        nodes.add(targetId);
        links.add(link);
      }
    });

    return { nodes, links };
  }, [focusNodeId, graphData.links]);

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

  const shouldFade = resultHighlightSet.size > 0 || !!focusNodeId;

  const graphDataToRender = useMemo(() => {
    if (!focusNodeId) {
      return graphData;
    }

    const focusedNodes = graphData.nodes.filter((node) => focusNeighborhood.nodes.has(node.id));
    const focusedLinks = graphData.links.filter((link) => focusNeighborhood.links.has(link));
    return {
      nodes: focusedNodes,
      links: focusedLinks,
    };
  }, [focusNeighborhood.links, focusNeighborhood.nodes, focusNodeId, graphData]);

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
    setSearchMatchNodeId(match.id);
    setFocusNodeId(match.id);

    if (graphRef.current && typeof match.x === "number" && typeof match.y === "number") {
      graphRef.current.centerAt(match.x, match.y, 700);
      graphRef.current.zoom(4, 700);
    }
  };

  const resetGraph = () => {
    setFocusNodeId(null);
    setSelectedNode(null);
    setHoveredNode(null);
    setSearchMatchNodeId(null);
    setSearchText("");
    if (graphRef.current) {
      graphRef.current.zoomToFit(600, 60);
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
        <button type="button" onClick={resetGraph}>
          Reset Graph
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
            graphData={graphDataToRender}
            nodeLabel={(node) => `${node.type}: ${node.label}`}
            nodeColor={(node) => {
              const nodeId = node.id;
              const baseColor = TYPE_COLORS[node.type] || TYPE_COLORS.Unknown;
              const isHighlighted = mergedHighlightNodes.has(nodeId);
              const isFocused = focusNodeId === nodeId;
              const isNeighbor = focusNodeId && focusNeighborhood.nodes.has(nodeId) && !isFocused;
              const isSearchMatch = searchMatchNodeId === nodeId;

              if (isFocused || isSearchMatch) {
                return baseColor;
              }

              if (isNeighbor) {
                return baseColor;
              }

              if (!shouldFade) {
                return isHighlighted || mergedHighlightNodes.size === 0 ? baseColor : "#cbd5e1";
              }

              if (isHighlighted) {
                return baseColor;
              }

              return "#e2e8f0";
            }}
            nodeRelSize={6}
            linkWidth={(link) => {
              const sourceId = getNodeId(link.source);
              const targetId = getNodeId(link.target);
              if (focusNodeId && (sourceId === focusNodeId || targetId === focusNodeId)) {
                return 3;
              }
              if (mergedHighlightLinks.has(link)) {
                return 2.2;
              }
              return 0.8;
            }}
            linkColor={(link) => {
              const sourceId = getNodeId(link.source);
              const targetId = getNodeId(link.target);
              if (focusNodeId && (sourceId === focusNodeId || targetId === focusNodeId)) {
                return "#0f172a";
              }
              if (mergedHighlightLinks.has(link)) {
                return "#1d4ed8";
              }
              return "#d1d5db";
            }}
            onNodeHover={setHoveredNode}
            onNodeClick={(node) => {
              setSelectedNode(node);
              setFocusNodeId(node?.id || null);
            }}
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
