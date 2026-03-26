import React, { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

function GraphView({ graphData, highlightedNodeIds = [] }) {
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!selectedNodeId) {
      return;
    }

    const existsInGraph = (graphData?.nodes || []).some((node) => String(node?.id) === selectedNodeId);
    if (!existsInGraph) {
      setSelectedNodeId("");
    }
  }, [graphData, selectedNodeId]);

  const safeGraph = useMemo(() => {
    const safeNodes = (Array.isArray(graphData?.nodes) ? graphData.nodes : []).map((node, index) => {
      const id = String(node?.id || index);
      return {
        ...node,
        id,
        label: String(node?.label || node?.id || index),
        type: String(node?.type || "Unknown"),
        source_entity: node?.source_entity || "Unknown",
      };
    });

    const validNodeIds = new Set(safeNodes.map((node) => node.id));
    const safeLinks = (Array.isArray(graphData?.links) ? graphData.links : [])
      .filter((link) => link && link.source !== undefined && link.target !== undefined)
      .map((link) => ({
        ...link,
        source: String(link.source),
        target: String(link.target),
      }))
      .filter((link) => validNodeIds.has(link.source) && validNodeIds.has(link.target));

    return { nodes: safeNodes, links: safeLinks };
  }, [graphData]);

  const nodeMap = useMemo(() => {
    const map = new Map();
    safeGraph.nodes.forEach((node) => map.set(node.id, node));
    return map;
  }, [safeGraph]);

  const neighborMap = useMemo(() => {
    const map = new Map();
    safeGraph.nodes.forEach((node) => map.set(node.id, new Set()));

    safeGraph.links.forEach((link) => {
      if (!map.has(link.source)) {
        map.set(link.source, new Set());
      }
      if (!map.has(link.target)) {
        map.set(link.target, new Set());
      }
      map.get(link.source).add(link.target);
      map.get(link.target).add(link.source);
    });

    return map;
  }, [safeGraph]);

  const highlightedSet = useMemo(
    () => new Set((highlightedNodeIds || []).map((id) => String(id))),
    [highlightedNodeIds]
  );

  const selectedNeighborSet = useMemo(() => {
    if (!selectedNodeId) {
      return new Set();
    }
    return new Set(Array.from(neighborMap.get(selectedNodeId) || []));
  }, [selectedNodeId, neighborMap]);

  const visibleNodeIdSet = useMemo(() => {
    if (!selectedNodeId) {
      return new Set(safeGraph.nodes.map((node) => node.id));
    }

    const visible = new Set([selectedNodeId]);
    selectedNeighborSet.forEach((id) => visible.add(id));
    return visible;
  }, [selectedNodeId, safeGraph.nodes, selectedNeighborSet]);

  const filteredGraph = useMemo(() => {
    const nodes = safeGraph.nodes.filter((node) => visibleNodeIdSet.has(node.id));
    const links = safeGraph.links.filter(
      (link) => visibleNodeIdSet.has(String(link.source)) && visibleNodeIdSet.has(String(link.target))
    );
    return { nodes, links };
  }, [safeGraph, visibleNodeIdSet]);

  const selectedNode = selectedNodeId ? nodeMap.get(selectedNodeId) : null;

  const searchMatches = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) {
      return new Set();
    }

    const matches = safeGraph.nodes
      .filter((node) => {
        const idMatch = String(node.id).toLowerCase().includes(term);
        const labelMatch = String(node.label || "").toLowerCase().includes(term);
        return idMatch || labelMatch;
      })
      .map((node) => node.id);

    return new Set(matches);
  }, [searchTerm, safeGraph]);

  const nodeColor = (node) => {
    const nodeId = String(node.id);

    if (searchTerm.trim() && searchMatches.has(nodeId)) {
      return "#f59e0b";
    }

    if (selectedNodeId) {
      if (nodeId === selectedNodeId) {
        return "#0ea5e9";
      }
      if (selectedNeighborSet.has(nodeId)) {
        return "#7dd3fc";
      }
      return "rgba(148, 163, 184, 0.35)";
    }

    if (highlightedSet.size > 0) {
      if (highlightedSet.has(nodeId)) {
        return "#06b6d4";
      }
      return "rgba(148, 163, 184, 0.3)";
    }

    return "#334155";
  };

  const nodeSize = (node) => {
    const nodeId = String(node.id);
    if (selectedNodeId && nodeId === selectedNodeId) {
      return 7;
    }
    if (searchTerm.trim() && searchMatches.has(nodeId)) {
      return 6;
    }
    if (highlightedSet.size > 0 && highlightedSet.has(nodeId)) {
      return 6;
    }
    return 4;
  };

  const nodeLabel = (node) => {
    const nodeId = String(node.id);
    const base = `${node.label || node.id}`;
    const meta = `type=${node.type}, source=${node.source_entity}`;

    if (selectedNodeId && nodeId === selectedNodeId) {
      return `${base}\n${meta}`;
    }
    if (highlightedSet.has(nodeId)) {
      return `${base}\n${meta}`;
    }
    return base;
  };

  const handleReset = () => {
    setSelectedNodeId("");
  };

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
        <div className="graph-header">
          <h2>ERP O2C Graph</h2>
          <span>{filteredGraph.nodes.length} nodes visible</span>
        </div>

        <div className="graph-toolbar">
          <input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search node id / order / invoice"
          />
          <button type="button" onClick={handleReset}>
            Reset View
          </button>
        </div>

        <div className="graph-canvas">
          <ForceGraph2D
            graphData={filteredGraph}
            nodeLabel={nodeLabel}
            nodeColor={nodeColor}
            nodeVal={nodeSize}
            linkColor={(link) => {
              if (!selectedNodeId && highlightedSet.size === 0) {
                return "rgba(148, 163, 184, 0.35)";
              }

              const source = String(link.source?.id || link.source);
              const target = String(link.target?.id || link.target);

              if (selectedNodeId) {
                const active =
                  source === selectedNodeId ||
                  target === selectedNodeId ||
                  (selectedNeighborSet.has(source) && selectedNeighborSet.has(target));
                return active ? "rgba(14, 165, 233, 0.8)" : "rgba(148, 163, 184, 0.18)";
              }

              const active = highlightedSet.has(source) && highlightedSet.has(target);
              return active ? "rgba(6, 182, 212, 0.8)" : "rgba(148, 163, 184, 0.18)";
            }}
            onNodeClick={(node) => setSelectedNodeId(String(node.id))}
            cooldownTicks={80}
          />

          {selectedNode ? (
            <aside
              style={{
                position: "absolute",
                top: 14,
                right: 14,
                width: 320,
                maxHeight: "75%",
                overflow: "auto",
                background: "rgba(255, 255, 255, 0.96)",
                border: "1px solid #dbe3ef",
                borderRadius: 10,
                padding: 12,
                boxShadow: "0 12px 28px rgba(15, 23, 42, 0.18)",
                zIndex: 3,
              }}
            >
              <h3 style={{ margin: 0, fontSize: 14 }}>Node details</h3>
              <p style={{ margin: "8px 0 0", fontSize: 12 }}>
                <strong>id:</strong> {selectedNode.id}
              </p>
              <p style={{ margin: "4px 0 0", fontSize: 12 }}>
                <strong>type:</strong> {selectedNode.type}
              </p>
              <p style={{ margin: "4px 0 0", fontSize: 12 }}>
                <strong>source_entity:</strong> {selectedNode.source_entity}
              </p>
              <pre
                style={{
                  marginTop: 10,
                  padding: 8,
                  borderRadius: 8,
                  background: "#f8fafc",
                  border: "1px solid #e5e7eb",
                  fontSize: 11,
                  whiteSpace: "pre-wrap",
                }}
              >
                {JSON.stringify(selectedNode, null, 2)}
              </pre>
            </aside>
          ) : null}
        </div>
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
