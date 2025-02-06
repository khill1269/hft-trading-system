from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from dataclasses import dataclass
import threading
from enum import Enum
import pandas as pd
from sklearn.preprocessing import StandardScaler

class VolatilityModel(Enum):
    GARCH = "GARCH"
    EWMA = "EWMA"
    HISTORICAL = "HISTORICAL"
    PARKINSON = "PARKINSON"
    COMBINED = "COMBINED"

@dataclass
class VolatilityForecast:
    symbol: str
    timestamp: datetime
    forecast_value: Decimal
    confidence_interval: Tuple[Decimal, Decimal]
    model_type: VolatilityModel
    forecast_horizon: int  # in minutes
    accuracy_score: float

class VolatilityForecaster:
    """Forecasts volatility using multiple models"""
    
    def __init__(
        self,
        market_data_manager,
        config: Dict,
        logger,
        error_handler
    ):
        self.market_data_manager = market_data_manager
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        # Model parameters
        self.lookback_window = config.get('volatility_lookback', 30)  # days
        self.forecast_horizons = [5, 15, 30, 60]  # minutes
        
        # Model weights for combination
        self._model_weights = {
            VolatilityModel.GARCH: Decimal('0.4'),
            VolatilityModel.EWMA: Decimal('0.3'),
            VolatilityModel.HISTORICAL: Decimal('0.1'),
            VolatilityModel.PARKINSON: Decimal('0.2')
        }
        
        # Model state
        self._forecasts: Dict[str, Dict[VolatilityModel, VolatilityForecast]] = {}
        self._model_accuracy: Dict[VolatilityModel, float] = {}
        
        # Data preprocessing
        self.scaler = StandardScaler()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Start forecast updater
        self._start_forecast_updater()
    
    async def get_volatility_forecast(
        self,
        symbol: str,
        horizon: int = 30,
        model: VolatilityModel = VolatilityModel.COMBINED
    ) -> Optional[VolatilityForecast]:
        """Get volatility forecast for a symbol"""
        try:
            with self._lock:
                if symbol not in self._forecasts:
                    await self._generate_forecasts(symbol)
                
                if model == VolatilityModel.COMBINED:
                    return self._combine_forecasts(symbol, horizon)
                
                forecasts = self._forecasts.get(symbol, {})
                return forecasts.get(model)
                
        except Exception as e:
            self.error_handler.handle_error(
                VolatilityForecastError(f"Forecast generation failed: {str(e)}")
            )
            return None
    
    async def _generate_forecasts(self, symbol: str) -> None:
        """Generate forecasts using all models"""
        # Get historical data
        data = await self._get_historical_data(symbol)
        if data is None or len(data) < self.lookback_window:
            raise VolatilityForecastError("Insufficient historical data")
        
        # Generate individual forecasts
        self._forecasts[symbol] = {}
        
        # GARCH forecast
        garch_forecast = await self._generate_garch_forecast(data)
        if garch_forecast:
            self._forecasts[symbol][VolatilityModel.GARCH] = garch_forecast
        
        # EWMA forecast
        ewma_forecast = self._generate_ewma_forecast(data)
        if ewma_forecast:
            self._forecasts[symbol][VolatilityModel.EWMA] = ewma_forecast
        
        # Historical forecast
        hist_forecast = self._generate_historical_forecast(data)
        if hist_forecast:
            self._forecasts[symbol][VolatilityModel.HISTORICAL] = hist_forecast
        
        # Parkinson forecast
        park_forecast = self._generate_parkinson_forecast(data)
        if park_forecast:
            self._forecasts[symbol][VolatilityModel.PARKINSON] = park_forecast
    
    async def _get_historical_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get and preprocess historical data"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=self.lookback_window)
        
        # Get OHLCV data
        data = await self.market_data_manager.get_historical_data(
            symbol, start_time, end_time
        )
        
        if not data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Remove outliers
        df = self._remove_outliers(df)
        
        return df
    
    async def _generate_garch_forecast(
        self,
        data: pd.DataFrame
    ) -> Optional[VolatilityForecast]:
        """Generate GARCH(1,1) forecast"""
        try:
            returns = data['returns'].dropna().values
            
            # Fit GARCH(1,1) model
            omega = np.var(returns) * 0.1
            alpha = 0.1
            beta = 0.8
            
            # Calculate volatility forecast
            h_t = omega
            for r in returns[-100:]:  # Use last 100 observations
                h_t = omega + alpha * r**2 + beta * h_t
            
            forecast_value = Decimal(str(np.sqrt(h_t * 252)))  # Annualized
            
            # Calculate confidence interval
            std_error = np.std(returns) * np.sqrt(252)
            ci_lower = Decimal(str(forecast_value - 1.96 * std_error))
            ci_upper = Decimal(str(forecast_value + 1.96 * std_error))
            
            return VolatilityForecast(
                symbol=data['symbol'].iloc[0],
                timestamp=datetime.utcnow(),
                forecast_value=forecast_value,
                confidence_interval=(ci_lower, ci_upper),
                model_type=VolatilityModel.GARCH,
                forecast_horizon=30,
                accuracy_score=self._model_accuracy.get(VolatilityModel.GARCH, 0.8)
            )
            
        except Exception as e:
            self.logger.log_error(e, "GARCH forecast generation failed")
            return None
    
    def _generate_ewma_forecast(
        self,
        data: pd.DataFrame
    ) -> Optional[VolatilityForecast]:
        """Generate EWMA forecast"""
        try:
            returns = data['returns'].dropna().values
            lambda_param = 0.94
            
            # Calculate EWMA volatility
            weights = np.array([(1-lambda_param) * lambda_param**i 
                              for i in range(len(returns))])
            weights = weights / weights.sum()
            
            vol = np.sqrt(np.sum(weights * returns**2) * 252)
            forecast_value = Decimal(str(vol))
            
            # Calculate confidence interval
            std_error = np.std(returns) * np.sqrt(252)
            ci_lower = Decimal(str(vol - 1.96 * std_error))
            ci_upper = Decimal(str(vol + 1.96 * std_error))
            
            return VolatilityForecast(
                symbol=data['symbol'].iloc[0],
                timestamp=datetime.utcnow(),
                forecast_value=forecast_value,
                confidence_interval=(ci_lower, ci_upper),
                model_type=VolatilityModel.EWMA,
                forecast_horizon=30,
                accuracy_score=self._model_accuracy.get(VolatilityModel.EWMA, 0.75)
            )
            
        except Exception as e:
            self.logger.log_error(e, "EWMA forecast generation failed")
            return None
    
    def _generate_historical_forecast(
        self,
        data: pd.DataFrame
    ) -> Optional[VolatilityForecast]:
        """Generate historical volatility forecast"""
        try:
            returns = data['returns'].dropna().values
            
            # Calculate historical volatility
            vol = np.std(returns) * np.sqrt(252)
            forecast_value = Decimal(str(vol))
            
            # Calculate confidence interval
            std_error = vol / np.sqrt(2 * (len(returns) - 1))
            ci_lower = Decimal(str(vol - 1.96 * std_error))
            ci_upper = Decimal(str(vol + 1.96 * std_error))
            
            return VolatilityForecast(
                symbol=data['symbol'].iloc[0],
                timestamp=datetime.utcnow(),
                forecast_value=forecast_value,
                confidence_interval=(ci_lower, ci_upper),
                model_type=VolatilityModel.HISTORICAL,
                forecast_horizon=30,
                accuracy_score=self._model_accuracy.get(VolatilityModel.HISTORICAL, 0.7)
            )
            
        except Exception as e:
            self.logger.log_error(e, "Historical forecast generation failed")
            return None
    
    def _generate_parkinson_forecast(
        self,
        data: pd.DataFrame
    ) -> Optional[VolatilityForecast]:
        """Generate Parkinson volatility forecast"""
        try:
            # Calculate Parkinson volatility
            high_low_ratio = np.log(data['high'] / data['low'])
            park_vol = np.sqrt(
                1 / (4 * np.log(2)) * 
                np.mean(high_low_ratio**2) * 
                252
            )
            forecast_value = Decimal(str(park_vol))
            
            # Calculate confidence interval
            std_error = park_vol / np.sqrt(2 * (len(data) - 1))
            ci_lower = Decimal(str(park_vol - 1.96 * std_error))
            ci_upper = Decimal(str(park_vol + 1.96 * std_error))
            
            return VolatilityForecast(
                symbol=data['symbol'].iloc[0],
                timestamp=datetime.utcnow(),
                forecast_value=forecast_value,
                confidence_interval=(ci_lower, ci_upper),
                model_type=VolatilityModel.PARKINSON,
                forecast_horizon=30,
                accuracy_score=self._model_accuracy.get(VolatilityModel.PARKINSON, 0.65)
            )
            
        except Exception as e:
            self.logger.log_error(e, "Parkinson forecast generation failed")
            return None
    
    def _combine_forecasts(
        self,
        symbol: str,
        horizon: int
    ) -> Optional[VolatilityForecast]:
        """Combine forecasts from different models"""
        try:
            forecasts = self._forecasts.get(symbol, {})
            if not forecasts:
                return None
            
            # Calculate weighted average
            weighted_sum = Decimal('0')
            weight_sum = Decimal('0')
            
            for model, forecast in forecasts.items():
                if model in self._model_weights:
                    weight = self._model_weights[model]
                    weighted_sum += forecast.forecast_value * weight
                    weight_sum += weight
            
            if weight_sum == 0:
                return None
            
            combined_forecast = weighted_sum / weight_sum
            
            # Calculate combined confidence interval
            ci_lower = min(f.confidence_interval[0] for f in forecasts.values())
            ci_upper = max(f.confidence_interval[1] for f in forecasts.values())
            
            return VolatilityForecast(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                forecast_value=combined_forecast,
                confidence_interval=(ci_lower, ci_upper),
                model_type=VolatilityModel.COMBINED,
                forecast_horizon=horizon,
                accuracy_score=max(f.accuracy_score for f in forecasts.values())
            )
            
        except Exception as e:
            self.logger.log_error(e, "Forecast combination failed")
            return None
    
    def _remove_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove outliers from data"""
        z_scores = stats.zscore(data['returns'].dropna())
        abs_z_scores = np.abs(z_scores)
        filtered_entries = abs_z_scores < 3  # Remove entries with z-score > 3
        return data[filtered_entries]
    
    def _start_forecast_updater(self) -> None:
        """Start forecast updating thread"""
        def updater_thread():
            while True:
                try:
                    self._update_model_accuracy()
                    self._update_forecasts()
                except Exception as e:
                    self.error_handler.handle_error(
                        VolatilityForecastError(f"Forecast update failed: {str(e)}")
                    )
                time.sleep(300)  # Update every 5 minutes
        
        thread = threading.Thread(target=updater_thread, daemon=True)
        thread.start()
    
    def _update_model_accuracy(self) -> None:
        """Update model accuracy scores"""
        # Compare previous forecasts with realized volatility
        pass
    
    def _update_forecasts(self) -> None:
        """Update all forecasts"""
        for symbol in self._forecasts.keys():
            asyncio.create_task(self._generate_forecasts(symbol))

class VolatilityForecastError(Exception):
    """Custom exception for volatility forecasting errors"""
    pass
