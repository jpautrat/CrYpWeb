"""
Backtesting framework for strategy validation.
Tests strategies on historical data with realistic execution simulation.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
from loguru import logger


class Backtester:
    """Backtests trading strategies on historical data"""
    
    def __init__(self, initial_capital: float = 500.0, fee_rate: float = 0.0016):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate  # 0.16% maker fee
    
    def simulate_execution(self, trades: pd.DataFrame, signals: pd.DataFrame,
                          slippage_bps: float = 2.0) -> pd.DataFrame:
        """
        Simulate order execution with slippage and fees.
        
        Args:
            trades: Historical trade data
            signals: Trading signals DataFrame with columns: timestamp, side, size, price
            slippage_bps: Slippage in basis points
        
        Returns:
            DataFrame with execution results
        """
        results = []
        capital = self.initial_capital
        position = 0.0
        entry_price = 0.0
        
        for idx, signal in signals.iterrows():
            timestamp = signal['timestamp']
            side = signal['side']
            size = signal['size']
            limit_price = signal.get('price', 0.0)
            
            # Find actual execution price (with slippage)
            relevant_trades = trades[trades['timestamp'] <= timestamp].tail(10)
            if not relevant_trades.empty:
                current_price = relevant_trades['price'].iloc[-1]
                
                if side == 'buy':
                    execution_price = current_price * (1 + slippage_bps / 10000)
                    cost = execution_price * size
                    fees = cost * self.fee_rate
                    
                    if capital >= (cost + fees):
                        capital -= (cost + fees)
                        position += size
                        entry_price = execution_price if position == size else entry_price
                        
                        results.append({
                            'timestamp': timestamp,
                            'side': side,
                            'size': size,
                            'price': execution_price,
                            'fees': fees,
                            'capital': capital,
                            'position': position
                        })
                
                elif side == 'sell' and position > 0:
                    execution_price = current_price * (1 - slippage_bps / 10000)
                    proceeds = execution_price * size
                    fees = proceeds * self.fee_rate
                    
                    if size <= position:
                        capital += (proceeds - fees)
                        position -= size
                        
                        pnl = (execution_price - entry_price) * size - fees
                        
                        results.append({
                            'timestamp': timestamp,
                            'side': side,
                            'size': size,
                            'price': execution_price,
                            'fees': fees,
                            'pnl': pnl,
                            'capital': capital,
                            'position': position
                        })
        
        return pd.DataFrame(results)
    
    def compute_metrics(self, results: pd.DataFrame) -> Dict:
        """Compute performance metrics"""
        if results.empty:
            return {}
        
        total_pnl = results['pnl'].sum() if 'pnl' in results.columns else 0.0
        total_fees = results['fees'].sum()
        
        returns = (results['capital'].pct_change()).dropna()
        
        metrics = {
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'net_profit': total_pnl - total_fees,
            'final_capital': results['capital'].iloc[-1],
            'return_pct': ((results['capital'].iloc[-1] - self.initial_capital) / self.initial_capital) * 100,
            'num_trades': len(results),
            'win_rate': (results['pnl'] > 0).mean() if 'pnl' in results.columns else 0.0,
            'avg_win': results[results['pnl'] > 0]['pnl'].mean() if 'pnl' in results.columns else 0.0,
            'avg_loss': results[results['pnl'] < 0]['pnl'].mean() if 'pnl' in results.columns else 0.0,
        }
        
        # Sharpe ratio (annualized)
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 24 * 60)  # Annualized
            metrics['sharpe_ratio'] = sharpe
        else:
            metrics['sharpe_ratio'] = 0.0
        
        # Maximum drawdown
        if 'capital' in results.columns:
            cumulative = results['capital']
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            metrics['max_drawdown'] = drawdown.min() * 100
        
        return metrics
