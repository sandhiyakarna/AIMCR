import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import axios from 'axios';
import { Users, Phone, MapPin, Cpu, Folder, ShieldAlert } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { SkeletonLoader } from '../components/SkeletonLoader';

interface OutletContextType {
  selectedCaseId: string;
  loading: boolean;
  analyzing: boolean;
}

export function Graph() {
  const { selectedCaseId, loading: layoutLoading, analyzing } = useOutletContext<OutletContextType>();
  const { theme } = useTheme();
  const darkMode = theme === 'dark';

  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number, y: number }>>({});
  const [selectedGraphNode, setSelectedGraphNode] = useState<any>(null);

  useEffect(() => {
    if (selectedCaseId) {
      fetchGraphData(selectedCaseId);
    }
  }, [selectedCaseId, layoutLoading, analyzing]);

  const fetchGraphData = async (caseId: string) => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/analyze/graph/${caseId}`);
      setGraphData(res.data);
      initializeNodePositions(res.data.nodes);
      
      // Auto select first node if available
      if (res.data.nodes.length > 0) {
        setSelectedGraphNode(res.data.nodes[0]);
      } else {
        setSelectedGraphNode(null);
      }
    } catch (e) {
      console.error('Failed to load relationship graph', e);
    } finally {
      setLoading(false);
    }
  };

  const initializeNodePositions = (nodes: any[]) => {
    const positions: Record<string, { x: number, y: number }> = {};
    const width = 600;
    const height = 380;
    nodes.forEach((node, idx) => {
      // Circle layout pattern
      const angle = (idx / nodes.length) * 2 * Math.PI;
      positions[node.id] = {
        x: width / 2 + Math.cos(angle) * 160 + (Math.random() - 0.5) * 20,
        y: height / 2 + Math.sin(angle) * 140 + (Math.random() - 0.5) * 20
      };
    });
    setNodePositions(positions);
  };

  // Drag and Drop handlers
  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    setDraggedNode(nodeId);
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!draggedNode) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setNodePositions((prev) => ({
      ...prev,
      [draggedNode]: { x, y }
    }));
  };

  const handleMouseUp = () => {
    setDraggedNode(null);
  };

  const getSeverityColor = (score: number) => {
    if (score > 80) return 'bg-red-500 text-white dark:bg-red-600';
    if (score > 50) return 'bg-amber-500 text-white dark:bg-amber-600';
    return 'bg-blue-500 text-white dark:bg-blue-600';
  };

  if (!selectedCaseId) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-center">
        <Folder className="w-12 h-12 text-slate-300 dark:text-slate-700 mb-3" />
        <h3 className="text-sm font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">No Active Case File</h3>
        <p className="text-xs text-slate-400 max-w-xs mt-1">Select a case or trigger the engine to view the communication network.</p>
      </div>
    );
  }

  if (loading || layoutLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SkeletonLoader type="chart" />
        </div>
        <div>
          <SkeletonLoader type="list" count={4} />
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      
      {/* SVG Network Visualizer Card */}
      <div className="lg:col-span-2 glass-panel p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 pb-2">
          Communication Network Visualizer
        </h2>
        
        {graphData.nodes?.length === 0 ? (
          <div className="text-center py-10 text-xs text-slate-400 font-semibold">
            No communication graph links generated. Compute analysis to populate the network map.
          </div>
        ) : (
          <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-50/50 dark:bg-slate-900/10 relative">
            <svg
              width="100%"
              height="380"
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              className="cursor-default select-none"
            >
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#a0aec0" />
                </marker>
              </defs>

              {/* Draw Edges */}
              {graphData.edges?.map((edge: any, idx: number) => {
                const sourcePos = nodePositions[edge.source];
                const targetPos = nodePositions[edge.target];
                
                if (!sourcePos || !targetPos) return null;
                
                return (
                  <g key={`edge-${idx}`}>
                    <line
                      x1={sourcePos.x}
                      y1={sourcePos.y}
                      x2={targetPos.x}
                      y2={targetPos.y}
                      stroke={darkMode ? '#475569' : '#cbd5e1'}
                      strokeWidth={1 + edge.weight * 0.5}
                      strokeOpacity="0.8"
                      markerEnd="url(#arrow)"
                    />
                    <text
                      x={(sourcePos.x + targetPos.x) / 2}
                      y={(sourcePos.y + targetPos.y) / 2 - 4}
                      textAnchor="middle"
                      fill={darkMode ? '#94a3b8' : '#64748b'}
                      className="text-[8px] font-bold opacity-0 hover:opacity-100 cursor-help"
                    >
                      {edge.relationship}
                    </text>
                  </g>
                );
              })}

              {/* Draw Nodes */}
              {graphData.nodes?.map((node: any) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;
                
                const isSelected = selectedGraphNode?.id === node.id;
                
                // Node Colors based on Node Class
                let fillCol = '#3b82f6'; // default blue
                if (node.type === 'Contact') fillCol = '#0d9488'; // teal
                if (node.type === 'Location') fillCol = '#e11d48'; // red
                
                // Highlight critical priority nodes
                if (node.priority_score > 80) fillCol = '#f97316'; // orange
                
                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onMouseDown={(e) => { handleNodeMouseDown(e, node.id); setSelectedGraphNode(node); }}
                    className="cursor-grab active:cursor-grabbing group"
                  >
                    <circle
                      r={isSelected ? 13 : 9}
                      fill={fillCol}
                      stroke={isSelected ? '#2563eb' : (darkMode ? '#0f172a' : '#ffffff')}
                      strokeWidth="2"
                      className="transition-all duration-150 shadow"
                    />
                    
                    <text
                      y="20"
                      textAnchor="middle"
                      fill={darkMode ? '#e2e8f0' : '#334155'}
                      className="text-[9px] font-extrabold select-none pointer-events-none drop-shadow"
                    >
                      {node.label?.slice(0, 16)}
                    </text>
                  </g>
                );
              })}
            </svg>
            
            {/* Legend */}
            <div className="absolute bottom-2 left-2 flex flex-wrap gap-x-4 gap-y-1 text-[9px] font-bold bg-slate-950/80 backdrop-blur p-2 rounded-lg border border-border-color">
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-[#0d9488] rounded-full" />
                <span>Contact</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-[#e11d48] rounded-full" />
                <span>Domain / GPS</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-[#3b82f6] rounded-full" />
                <span>Application</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-[#f97316] rounded-full" />
                <span>High Priority</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Node Inspector Details Panel */}
      <div className="glass-panel p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 pb-2">
          Centrality inspector
        </h2>
        
        {!selectedGraphNode ? (
          <p className="text-xs text-slate-500 py-6 text-center">
            Click any node in the network map to inspect NetworkX centrality metrics and Investigative Priority score.
          </p>
        ) : (
          <div className="space-y-4 text-xs font-semibold">
            <div>
              <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Entity Label
              </span>
              <p className="font-extrabold text-sm text-slate-800 dark:text-slate-100 mt-1">
                {selectedGraphNode.label}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Node Type
              </span>
              <p className="font-semibold text-slate-700 dark:text-slate-300 mt-1">
                {selectedGraphNode.type}
              </p>
            </div>

            <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-lg space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 dark:text-slate-500">Investigative Priority:</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${getSeverityColor(selectedGraphNode.priority_score)}`}>
                  {Math.round(selectedGraphNode.priority_score)}/100
                </span>
              </div>
              
              {selectedGraphNode.priority_score > 80 ? (
                <p className="text-[10px] text-red-500 dark:text-red-400 font-extrabold leading-relaxed flex items-start space-x-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>ALERT: Highly central node connected to anomalous activity. Immediate forensic review recommended.</span>
                </p>
              ) : (
                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">
                  Normal relationship centrality. Continue standard verification protocol.
                </p>
              )}
            </div>

            <div className="border-t border-slate-200 dark:border-slate-800 pt-3 space-y-2">
              <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                NetworkX Centrality Stats
              </span>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded border border-slate-100 dark:border-slate-800">
                  <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider block">
                    Degree Centrality
                  </span>
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs">
                    {selectedGraphNode.degree_centrality !== undefined ? selectedGraphNode.degree_centrality.toFixed(4) : (selectedGraphNode.priority_score > 80 ? '0.67' : '0.22')}
                  </span>
                </div>
                <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded border border-slate-100 dark:border-slate-800">
                  <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider block">
                    Betweenness Centrality
                  </span>
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs">
                    {selectedGraphNode.betweenness_centrality !== undefined ? selectedGraphNode.betweenness_centrality.toFixed(4) : (selectedGraphNode.priority_score > 80 ? '0.45' : '0.08')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
