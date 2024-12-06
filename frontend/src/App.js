import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  AppBar,
  Toolbar,
  Card,
  CardContent,
  Alert,
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

function App() {
  const [metrics, setMetrics] = useState({
    heartRate: [],
    steps: 0,
    sleep: 0,
    hrv: 0,
  });
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    socket.on('metrics_update', (data) => {
      setMetrics(prev => ({
        ...prev,
        heartRate: [...prev.heartRate, data.metrics.heart_rate].slice(-20),
        steps: data.metrics.steps,
        sleep: data.metrics.sleep_hours,
        hrv: data.metrics.hrv,
      }));
    });

    socket.on('risk_alert', (data) => {
      setAlerts(prev => [...prev, data]);
    });

    return () => {
      socket.off('metrics_update');
      socket.off('risk_alert');
    };
  }, []);

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" sx={{ backgroundColor: '#1a237e' }}>
        <Toolbar>
          <Typography variant="h6">
            Athlete Digital Twin - Anti-Doping Monitor
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        {alerts.map((alert, index) => (
          <Alert severity="error" sx={{ mb: 2 }} key={index}>
            {alert.message} - Supplement: {alert.supplement}
          </Alert>
        ))}

        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2, height: '100%' }}>
              <Typography variant="h6" gutterBottom>
                Heart Rate Monitoring
              </Typography>
              <LineChart width={700} height={300} data={metrics.heartRate.map((hr, index) => ({ time: index, value: hr }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#8884d8" />
              </LineChart>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Daily Steps
                    </Typography>
                    <Typography variant="h4">
                      {metrics.steps.toLocaleString()}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Sleep Hours
                    </Typography>
                    <Typography variant="h4">
                      {metrics.sleep}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      HRV Score
                    </Typography>
                    <Typography variant="h4">
                      {metrics.hrv}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

export default App;
