"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type {
  LineageGraphResponse,
  LineageNodeData,
} from "@/types";
import { getMoneyLineage } from "@/lib/api";

// ─── Visual Status Helpers ───────────────────────────────────────────────────

function getStatusStyling(visualStatus: string, isMissing: boolean) {
  if (isMissing) {
    return {
      border: "border-2 border-dashed border-rose-500/60",
      bg: "bg-gradient-to-b from-rose-950/30 to-zinc-950/80",
      pillBg: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
      dot: "bg-rose-500 animate-pulse",
      glow: "shadow-[0_0_15px_rgba(244,63,94,0.15)]",
    };
  }

  switch (visualStatus) {
    case "green":
      return {
        border: "border border-emerald-500/50 hover:border-emerald-400",
        bg: "bg-gradient-to-b from-emerald-950/25 to-slate-900/90",
        pillBg: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30",
        dot: "bg-emerald-400",
        glow: "shadow-[0_0_12px_rgba(16,185,129,0.15)]",
      };
    case "yellow":
      return {
        border: "border border-amber-500/60 hover:border-amber-400",
        bg: "bg-gradient-to-b from-amber-950/25 to-slate-900/90",
        pillBg: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
        dot: "bg-amber-400 animate-pulse",
        glow: "shadow-[0_0_12px_rgba(245,158,11,0.15)]",
      };
    case "red":
      return {
        border: "border-2 border-rose-500/70 hover:border-rose-400",
        bg: "bg-gradient-to-b from-rose-950/35 to-slate-900/95",
        pillBg: "bg-rose-500/20 text-rose-300 border border-rose-500/40",
        dot: "bg-rose-400 animate-ping",
        glow: "shadow-[0_0_20px_rgba(244,63,94,0.25)]",
      };
    case "blue":
      return {
        border: "border border-sky-500/50 hover:border-sky-400",
        bg: "bg-gradient-to-b from-sky-950/25 to-slate-900/90",
        pillBg: "bg-sky-500/15 text-sky-300 border border-sky-500/30",
        dot: "bg-sky-400",
        glow: "shadow-[0_0_12px_rgba(14,165,233,0.15)]",
      };
    case "grey":
    default:
      return {
        border: "border border-dashed border-zinc-600 hover:border-zinc-500",
        bg: "bg-gradient-to-b from-zinc-900/40 to-slate-900/90",
        pillBg: "bg-zinc-800/60 text-zinc-400 border border-zinc-700/40",
        dot: "bg-zinc-500",
        glow: "",
      };
  }
}

function getCategoryIcon(category: string) {
  switch (category) {
    case "ORDER":
      return "🛍️";
    case "PAYMENT":
      return "💳";
    case "FEE":
      return "🏷️";
    case "TAX":
      return "⚖️";
    case "SETTLEMENT":
      return "📑";
    case "BANK_CREDIT":
      return "🏦";
    case "LEDGER":
      return "📖";
    case "SHIPMENT":
      return "🚚";
    case "REFUND":
      return "🔄";
    case "EXCEPTION":
      return "🚨";
    default:
      return "🔹";
  }
}

// ─── Custom Lineage Node Component ───────────────────────────────────────────

type CustomLineageNodeType = Node<LineageNodeData, "lineageNode">;
type CustomNodeProps = NodeProps<CustomLineageNodeType>;

function CustomLineageNode({ data, selected }: CustomNodeProps) {
  const styling = getStatusStyling(data.visual_status, data.is_missing);
  const icon = getCategoryIcon(data.category);

  return (
    <div
      className={`relative min-w-[210px] max-w-[250px] rounded-xl p-3.5 backdrop-blur-md transition-all duration-200 cursor-pointer select-none text-left ${styling.bg} ${styling.border} ${styling.glow} ${
        selected ? "ring-2 ring-indigo-400 scale-[1.03] shadow-[0_0_25px_rgba(99,102,241,0.4)]" : ""
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-indigo-400 !border-2 !border-slate-900 !-top-1.5"
      />

      {/* Header: Category & Visual Dot */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-base leading-none">{icon}</span>
          <span className="text-[10px] font-bold tracking-wider uppercase text-slate-400 truncate">
            {data.category.replace("_", " ")}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className={`inline-block w-2 h-2 rounded-full ${styling.dot}`} />
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${styling.pillBg}`}>
            {data.status_label}
          </span>
        </div>
      </div>

      {/* Title / Record ID */}
      <div className="text-xs font-semibold text-slate-100 truncate mb-1">
        {data.title}
      </div>

      {/* Amount & Date / Details */}
      <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-slate-700/40">
        <div className="text-[13px] font-bold tracking-tight text-white">
          {data.amount_inr || (data.is_missing ? "N/A" : "—")}
        </div>
        {data.date && (
          <div className="text-[10px] text-slate-400 truncate">
            {data.date.split(" ")[0]}
          </div>
        )}
      </div>

      {/* Discrepancy indicator if missing */}
      {data.is_missing && (
        <div className="mt-1.5 text-[10px] text-rose-300 font-medium bg-rose-950/40 border border-rose-800/40 rounded px-1.5 py-0.5 truncate">
          ⚠️ {data.discrepancy || "Record Missing"}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-indigo-400 !border-2 !border-slate-900 !-bottom-1.5"
      />
    </div>
  );
}

// ─── Main MoneyLineageGraph Component ─────────────────────────────────────────

interface MoneyLineageGraphProps {
  entityType: string;
  entityId: string;
  className?: string;
  onNodeClick?: (nodeData: LineageNodeData) => void;
}

export default function MoneyLineageGraph({
  entityType,
  entityId,
  className = "h-[500px]",
  onNodeClick,
}: MoneyLineageGraphProps) {
  const [graphData, setGraphData] = useState<LineageGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<LineageNodeData | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<CustomLineageNodeType>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const nodeTypes = useMemo(
    () => ({
      lineageNode: CustomLineageNode,
    }),
    []
  );

  const fetchGraph = useCallback(async () => {
    if (!entityType || !entityId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getMoneyLineage(entityType, entityId);
      setGraphData(data);

      const flowNodes: CustomLineageNodeType[] = data.nodes.map((n) => ({
        id: n.id,
        type: "lineageNode" as const,
        position: n.position,
        data: n.data,
      }));

      const flowEdges: Edge[] = data.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label ?? undefined,
        animated: e.animated,
        style: e.style ?? { stroke: "#64748b" },
        labelStyle: { fill: "#94a3b8", fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: "#0f172a", fillOpacity: 0.85 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);

      // Select root or problematic node by default
      const rootNode = flowNodes.find((n) => n.id.includes(entityId));
      if (rootNode) {
        setSelectedNodeData(rootNode.data as unknown as LineageNodeData);
      } else if (flowNodes.length > 0) {
        setSelectedNodeData(flowNodes[0].data as unknown as LineageNodeData);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load money lineage graph.");
    } finally {
      setLoading(false);
    }
  }, [entityType, entityId, setNodes, setEdges]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    const data = node.data as unknown as LineageNodeData;
    setSelectedNodeData(data);
    if (onNodeClick) {
      onNodeClick(data);
    }
  };

  return (
    <div className={`relative flex flex-col rounded-2xl bg-slate-950/80 border border-slate-800 overflow-hidden ${className}`}>
      {/* Top Header Summary Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-slate-900/90 border-b border-slate-800/80 z-10 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
          <div>
            <div className="text-xs font-bold text-white flex items-center gap-2">
              <span>Money Lineage Journey</span>
              <span className="text-[11px] font-mono text-indigo-300 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/40">
                {entityType.toUpperCase()}: {entityId}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Deterministic multi-hop audit trail across cart, gateway, bank, and accounting ledger.
            </p>
          </div>
        </div>

        {graphData && (
          <div className="flex items-center gap-2 flex-wrap">
            <div className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 ${
              graphData.summary.status === "VERIFIED"
                ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                : "bg-rose-500/15 text-rose-300 border border-rose-500/40"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                graphData.summary.status === "VERIFIED" ? "bg-emerald-400" : "bg-rose-400 animate-pulse"
              }`} />
              {graphData.summary.status === "VERIFIED" ? "Chain Verified" : "Chain Broken / At Risk"}
            </div>

            <div className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/60">
              Gross: <span className="font-semibold text-white">{graphData.summary.gross_amount_inr}</span>
            </div>
            <div className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/60">
              Net Settled: <span className="font-semibold text-emerald-400">{graphData.summary.net_settled_inr}</span>
            </div>
          </div>
        )}
      </div>

      {/* Break point alert if chain broken */}
      {graphData?.summary.break_point && (
        <div className="flex items-center gap-2 px-4 py-2 bg-rose-950/40 border-b border-rose-800/40 text-xs text-rose-300 font-medium z-10">
          <span className="text-rose-400 font-bold">⚠️ Root Cause:</span>
          <span>{graphData.summary.break_point}</span>
        </div>
      )}

      {/* Main Canvas & Inspector Drawer */}
      <div className="relative flex-1 w-full min-h-[360px] overflow-hidden">
        {loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 z-20 backdrop-blur-sm">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-2" />
            <span className="text-xs text-slate-400 font-medium">Tracing money lineage across systems...</span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/90 z-20 p-6 text-center">
            <div className="text-2xl mb-2">⚠️</div>
            <div className="text-sm font-semibold text-rose-400 mb-1">Failed to trace lineage</div>
            <p className="text-xs text-slate-400 max-w-md mb-4">{error}</p>
            <button
              onClick={fetchGraph}
              className="px-3 py-1.5 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition"
            >
              Retry Journey Trace
            </button>
          </div>
        )}

        {/* React Flow Canvas */}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.2}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
          colorMode="dark"
          className="bg-[#0b101b]"
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={18}
            size={1.2}
            color="#1e293b"
          />
          <Controls
            showZoom={true}
            showFitView={true}
            showInteractive={true}
            position="bottom-left"
            className="!bg-slate-900 !border-slate-700 !rounded-xl overflow-hidden !shadow-2xl"
          />
          <MiniMap
            nodeColor={(node) => {
              const d = node.data as unknown as LineageNodeData;
              if (d?.is_missing) return "#ef4444";
              if (d?.visual_status === "green") return "#10b981";
              if (d?.visual_status === "yellow") return "#f59e0b";
              if (d?.visual_status === "blue") return "#0ea5e9";
              return "#64748b";
            }}
            maskColor="rgba(15, 23, 42, 0.75)"
            className="!bg-slate-900/90 !border-slate-800 !rounded-xl overflow-hidden !shadow-2xl"
          />
        </ReactFlow>

        {/* Node Inspection Slide-over / Sheet (Right side) */}
        {selectedNodeData && (
          <div className="absolute right-3 top-3 bottom-3 w-80 max-w-[90%] bg-slate-900/95 border border-slate-700/80 rounded-xl p-4 shadow-2xl backdrop-blur-xl z-20 flex flex-col overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">{getCategoryIcon(selectedNodeData.category)}</span>
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    {selectedNodeData.category.replace("_", " ")}
                  </h4>
                  <p className="text-[10px] text-slate-400 font-mono">
                    {selectedNodeData.record_id}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedNodeData(null)}
                className="text-slate-400 hover:text-white text-xs p-1 rounded hover:bg-slate-800"
                title="Close Inspector"
              >
                ✕
              </button>
            </div>

            {/* Status & Amount */}
            <div className="space-y-2 mb-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Status</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${getStatusStyling(selectedNodeData.visual_status, selectedNodeData.is_missing).pillBg}`}>
                  {selectedNodeData.status_label}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Amount</span>
                <span className="font-bold text-white text-sm">
                  {selectedNodeData.amount_inr || "N/A"}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Source System</span>
                <span className="text-slate-200 font-medium truncate max-w-[150px]">
                  {selectedNodeData.source_system}
                </span>
              </div>
              {selectedNodeData.date && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Timestamp</span>
                  <span className="text-slate-300 font-mono text-[11px]">
                    {selectedNodeData.date}
                  </span>
                </div>
              )}
            </div>

            {/* Discrepancy warning box */}
            {selectedNodeData.discrepancy && (
              <div className="mb-3 p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
                <div className="font-bold mb-0.5 flex items-center gap-1 text-rose-200">
                  <span>⚠️ Discrepancy Detected</span>
                </div>
                <p className="text-[11px] leading-relaxed text-rose-300/90">
                  {selectedNodeData.discrepancy}
                </p>
              </div>
            )}

            {/* Deterministic Verification Rule */}
            {selectedNodeData.rule && (
              <div className="mb-3 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">
                  Deterministic Verification Rule
                </div>
                <p className="text-[11px] text-slate-300 font-mono leading-relaxed">
                  {selectedNodeData.rule}
                </p>
                {selectedNodeData.confidence !== null && selectedNodeData.confidence !== undefined && (
                  <div className="mt-2 text-[10px] text-slate-400 flex items-center justify-between">
                    <span>Rule Confidence</span>
                    <span className="text-indigo-400 font-bold">
                      {selectedNodeData.confidence === 1.0 || selectedNodeData.confidence === 100.0
                        ? "100% Deterministic"
                        : `${selectedNodeData.confidence}%`}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Key-Value Details */}
            {selectedNodeData.details && Object.keys(selectedNodeData.details).length > 0 && (
              <div className="mt-auto pt-2 border-t border-slate-800/80">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-2">
                  System Attributes
                </div>
                <div className="space-y-1.5">
                  {Object.entries(selectedNodeData.details).map(([k, v]) => (
                    <div key={k} className="flex items-start justify-between gap-2 text-[11px]">
                      <span className="text-slate-400 truncate">{k}</span>
                      <span className="text-slate-200 font-mono text-right truncate max-w-[150px]">
                        {String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 bg-slate-950 border-t border-slate-800 text-[10px] text-slate-400">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-semibold text-slate-300">Legend:</span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Verified
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Pending Delay
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-400" /> Mismatch / High Risk
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-sky-400" /> Fee / Tax Schedule
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-zinc-500" /> Missing Record
          </span>
        </div>
        <div className="text-slate-500 text-[10px]">
          Click any node to inspect audit proof & source records
        </div>
      </div>
    </div>
  );
}
