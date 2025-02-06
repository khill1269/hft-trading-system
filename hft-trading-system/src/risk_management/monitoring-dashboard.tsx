import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar
} from 'recharts';
import { 
  AlertCircle, TrendingUp, DollarSign, Activity, 
  BarChart2, Clock, Bell 
} from 'lucide-react';
import { 
  Card, CardContent, CardDescription, CardHeader, CardTitle 
} from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const MonitoringDashboard = () => {
  const [tradingMetrics, setTradingMetrics] = useState({
    pnl: 0,
    totalTrades: 0,
    winRate: 0,
    activePositions: 0
  });
  
  const [systemMetrics, setSystemMetrics] = useState({
    orderLatency: 0,
    systemLoad: 0,
    errorRate: 0,
    uptime: 0
  });
  
  const [alerts, setAlerts] = useState([]);
  const [tradingHistory, setTradingHistory] = useState([]);
  const [positionData, setPositionData] = useState([]);
  
  // Simulated data fetching
  useEffect(() => {
    // Simulated real-time updates
    const interval = setInterval(() => {
      updateMetrics();
      updateAlerts();
      updateTradingHistory();
      updatePositionData();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);
  
  const updateMetrics = () => {
    setTradingMetrics({
      pnl: Math.random() * 10000,
      totalTrades: Math.floor(Math.random() * 1000),
      winRate: Math.random() * 100,
      activePositions: Math.floor(Math.random() * 20)
    });
    
    setSystemMetrics({
      orderLatency: Math.random() * 100,
      systemLoad: Math.random() * 100,
      errorRate: Math.random() * 5,
      uptime: 99.9
    });
  };
  
  const updateAlerts = () => {
    const newAlert = {
      id: Date.now(),
      type: Math.random() > 0.5 ? 'warning' : 'error',
      message: `Alert ${Date.now()}`,
      timestamp: new Date().toISOString()
    };
    setAlerts(prev => [...prev.slice(-4), newAlert]);
  };
  
  const updateTradingHistory = () => {
    const newData = {
      timestamp: new Date().toISOString(),
      pnl: Math.random() * 1000 - 500,
      trades: Math.floor(Math.random() * 10)
    };
    setTradingHistory(prev => [...prev.slice(-19), newData]);
  };
  
  const updatePositionData = () => {
    const positions = [
      { symbol: 'AAPL', value: Math.random() * 10000 },
      { symbol: 'GOOGL', value: Math.random() * 10000 },
      { symbol: 'MSFT', value: Math.random() * 10000 },
      { symbol: 'AMZN', value: Math.random() * 10000 }
    ];
    setPositionData(positions);
  };

  return (
    <div className="p-4 bg-gray-100 min-h-screen">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Trading System Monitor</h1>
        <p className="text-gray-600">Real-time system performance and metrics</p>
      </div>

      {/* Trading Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              <DollarSign className="h-4 w-4 inline mr-1" />
              P&L
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${tradingMetrics.pnl.toFixed(2)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              <Activity className="h-4 w-4 inline mr-1" />
              Total Trades
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tradingMetrics.totalTrades}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              <TrendingUp className="h-4 w-4 inline mr-1" />
              Win Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tradingMetrics.winRate.toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              <BarChart2 className="h-4 w-4 inline mr-1" />
              Active Positions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tradingMetrics.activePositions}</div>
          </CardContent>
        </Card>
      </div>

      {/* System Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Order Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemMetrics.orderLatency.toFixed(2)}ms
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">System Load</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemMetrics.systemLoad.toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemMetrics.errorRate.toFixed(2)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemMetrics.uptime.toFixed(2)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Trading History Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Trading Performance</CardTitle>
            <CardDescription>P&L and trade volume over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={tradingHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="timestamp" 
                    tick={{fontSize: 12}}
                    tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                  />
                  <YAxis tick={{fontSize: 12}} />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="pnl" 
                    stroke="#8884d8" 
                    name="P&L"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="trades" 
                    stroke="#82ca9d" 
                    name="Trades"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Position Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Position Distribution</CardTitle>
            <CardDescription>Current position values by symbol</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={positionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8" name="Position Value" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      <Card>
        <CardHeader>
          <CardTitle>
            <Bell className="h-4 w-4 inline mr-2" />
            System Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {alerts.map(alert => (
              <Alert key={alert.id} variant={alert.type === 'error' ? 'destructive' : 'default'}>
                <AlertCircle className="h-4 w-4" />
                <AlertTitle className="ml-2">
                  {alert.type === 'error' ? 'Error' : 'Warning'}
                </AlertTitle>
                <AlertDescription className="ml-2">
                  {alert.message} - {new Date(alert.timestamp).toLocaleTimeString()}
                </AlertDescription>
              </Alert>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MonitoringDashboard;
