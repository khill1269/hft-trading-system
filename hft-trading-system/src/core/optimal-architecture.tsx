import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ArchitectureNode = ({ title, items, type }) => {
  const getTypeStyles = () => {
    switch(type) {
      case 'core':
        return 'bg-blue-100 border-blue-300';
      case 'optimization':
        return 'bg-green-100 border-green-300';
      case 'processing':
        return 'bg-purple-100 border-purple-300';
      case 'monitoring':
        return 'bg-orange-100 border-orange-300';
      default:
        return 'bg-gray-100 border-gray-300';
    }
  };

  return (
    <div className={`p-4 rounded-lg border ${getTypeStyles()}`}>
      <h3 className="font-bold text-sm mb-2">{title}</h3>
      <ul className="text-xs space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-2">
            <div className="w-1 h-1 rounded-full bg-gray-600" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
};

const DataFlow = () => (
  <div className="absolute inset-0 pointer-events-none">
    <svg className="w-full h-full" style={{ position: 'absolute', zIndex: 0 }}>
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
        </marker>
      </defs>
    </svg>
  </div>
);

const OptimalArchitecture = () => {
  const components = {
    infrastructure: {
      title: "Core Infrastructure",
      type: "core",
      items: [
        "FPGA-Accelerated Processing",
        "Lock-free Ring Buffers",
        "Kernel-optimized Networking",
        "Multi-tiered Caching",
        "Distributed Event Processing"
      ]
    },
    optimization: {
      title: "Optimization Layer",
      type: "optimization",
      items: [
        "Dynamic CPU/Memory Allocation",
        "Adaptive Network Routing",
        "Predictive Data Prefetching",
        "Hardware-Software Co-optimization",
        "Quantum-inspired Algorithms"
      ]
    },
    execution: {
      title: "Execution Engine",
      type: "processing",
      items: [
        "Smart Order Routing",
        "Real-time Risk Checks",
        "Hardware-accelerated Matching",
        "Adaptive Execution Strategies",
        "Sub-microsecond Processing"
      ]
    },
    data: {
      title: "Market Data Processing",
      type: "processing",
      items: [
        "Order Book Reconstruction",
        "Market Microstructure Analysis",
        "Real-time Signal Generation",
        "Cross-market Arbitrage Detection",
        "Sentiment Analysis Integration"
      ]
    },
    ai: {
      title: "AI/ML Systems",
      type: "processing",
      items: [
        "Deep Reinforcement Learning",
        "Adaptive Strategy Selection",
        "Online Model Updates",
        "Feature Engineering Pipeline",
        "Model Performance Monitoring"
      ]
    },
    monitoring: {
      title: "System Monitoring",
      type: "monitoring",
      items: [
        "Nanosecond Precision Latency",
        "Hardware Resource Monitoring",
        "Performance Analytics",
        "Anomaly Detection",
        "Circuit Breaker Management"
      ]
    },
    risk: {
      title: "Risk Management",
      type: "monitoring",
      items: [
        "Real-time Position Tracking",
        "Dynamic Risk Limits",
        "Market Impact Analysis",
        "Emergency Position Management",
        "Cross-asset Risk Calculation"
      ]
    },
    config: {
      title: "Configuration & Deployment",
      type: "core",
      items: [
        "Environment Management",
        "Secrets Encryption",
        "Dynamic Configuration",
        "Deployment Automation",
        "System Health Checks"
      ]
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Optimal HFT System Architecture</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-4 relative">
          <DataFlow />
          {Object.entries(components).map(([key, { title, items, type }]) => (
            <ArchitectureNode 
              key={key}
              title={title}
              items={items}
              type={type}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default OptimalArchitecture;