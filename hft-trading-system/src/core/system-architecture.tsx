import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const SystemComponent = ({ title, items, className = '' }) => (
  <div className={`border rounded-lg p-4 ${className}`}>
    <h3 className="font-semibold mb-2">{title}</h3>
    <ul className="text-sm space-y-1">
      {items.map((item, i) => (
        <li key={i} className="flex items-center">
          <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
          {item}
        </li>
      ))}
    </ul>
  </div>
);

const SystemArchitecture = () => {
  const components = {
    core: {
      title: "Core Infrastructure",
      items: [
        "FPGA-Accelerated Processing",
        "Distributed Event Processing",
        "Advanced Circuit Breakers",
        "Multi-DB Architecture"
      ]
    },
    marketData: {
      title: "Market Data System",
      items: [
        "Ultra-Low Latency Processing",
        "Order Book Reconstruction",
        "Real-time Analytics",
        "Multi-source Integration"
      ]
    },
    trading: {
      title: "Trading Engine",
      items: [
        "Smart Order Routing",
        "Execution Optimization",
        "Adaptive Algorithms",
        "Co-location Support"
      ]
    },
    risk: {
      title: "Risk Management",
      items: [
        "Real-time Risk Monitoring",
        "Position Management",
        "Dynamic Risk Limits",
        "Market Impact Analysis"
      ]
    },
    ai: {
      title: "AI/ML Systems",
      items: [
        "Deep Reinforcement Learning",
        "Quantum Optimization",
        "Predictive Analytics",
        "Adaptive Strategies"
      ]
    },
    monitoring: {
      title: "Monitoring & Analytics",
      items: [
        "Performance Analytics",
        "System Health Monitoring",
        "Latency Analysis",
        "Market Microstructure"
      ]
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Enhanced HFT System Architecture</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(components).map(([key, { title, items }]) => (
            <SystemComponent 
              key={key}
              title={title}
              items={items}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default SystemArchitecture;