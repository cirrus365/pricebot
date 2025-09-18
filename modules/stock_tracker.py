"""
Stock market data tracker using yfinance
"""
import logging
import yfinance as yf
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StockTracker:
    """Handles fetching and formatting stock market data"""
    
    @classmethod
    def format_currency(cls, value: float) -> str:
        """Format currency values"""
        if value >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        else:
            return f"${value:.2f}"
    
    @classmethod
    def format_percentage(cls, value: float) -> str:
        """Format percentage with color indicators"""
        if value > 0:
            return f"📈 +{value:.2f}%"
        elif value < 0:
            return f"📉 {value:.2f}%"
        else:
            return f"➡️ {value:.2f}%"
    
    @classmethod
    def format_volume(cls, volume: int) -> str:
        """Format volume numbers"""
        if volume >= 1_000_000_000:
            return f"{volume/1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume/1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume/1_000:.2f}K"
        else:
            return str(volume)
    
    @classmethod
    async def get_stock_info(cls, ticker: str) -> Optional[str]:
        """Get comprehensive stock information"""
        try:
            # Clean the ticker symbol
            ticker = ticker.upper().strip()
            
            # Create ticker object
            stock = yf.Ticker(ticker)
            
            # Get stock info
            info = stock.info
            
            # Check if we got valid data
            if not info or 'regularMarketPrice' not in info:
                # Try alternative method
                hist = stock.history(period="1d")
                if hist.empty:
                    return f"❌ Could not find stock data for '{ticker}'. Please check the ticker symbol."
                
                # Use historical data as fallback
                current_price = hist['Close'].iloc[-1]
                volume = hist['Volume'].iloc[-1]
                
                # Get 5 day history for change calculation
                hist_5d = stock.history(period="5d")
                if len(hist_5d) >= 2:
                    prev_close = hist_5d['Close'].iloc[-2]
                    change = current_price - prev_close
                    change_percent = (change / prev_close) * 100
                else:
                    change = 0
                    change_percent = 0
                
                # Basic response with limited data
                response = f"""📊 **Stock Info: {ticker}**

💵 **Current Price:** {cls.format_currency(current_price)}
{cls.format_percentage(change_percent)} ({cls.format_currency(abs(change))})
📊 **Volume:** {cls.format_volume(int(volume))}"""
                
                return response
            
            # Extract key information
            current_price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
            prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)
            open_price = info.get('regularMarketOpen') or info.get('open', 0)
            day_high = info.get('regularMarketDayHigh') or info.get('dayHigh', 0)
            day_low = info.get('regularMarketDayLow') or info.get('dayLow', 0)
            volume = info.get('regularMarketVolume') or info.get('volume', 0)
            avg_volume = info.get('averageVolume', 0)
            market_cap = info.get('marketCap', 0)
            
            # Calculate changes
            change = current_price - prev_close if prev_close else 0
            change_percent = (change / prev_close * 100) if prev_close else 0
            
            # Get additional info
            company_name = info.get('longName') or info.get('shortName', ticker)
            exchange = info.get('exchange', 'N/A')
            currency = info.get('currency', 'USD')
            
            # Get 52 week data
            week_52_high = info.get('fiftyTwoWeekHigh', 0)
            week_52_low = info.get('fiftyTwoWeekLow', 0)
            
            # Get averages
            ma_50 = info.get('fiftyDayAverage', 0)
            ma_200 = info.get('twoHundredDayAverage', 0)
            
            # Get fundamentals
            pe_ratio = info.get('trailingPE', 0)
            forward_pe = info.get('forwardPE', 0)
            dividend_yield = info.get('dividendYield', 0)
            beta = info.get('beta', 0)
            
            # Build response
            response = f"""📊 **Stock Info: {company_name} ({ticker})**
🏢 Exchange: {exchange} | Currency: {currency}

💵 **Current Price:** {cls.format_currency(current_price)}
{cls.format_percentage(change_percent)} ({cls.format_currency(abs(change))})

📈 **Today's Trading:**
• Open: {cls.format_currency(open_price)}
• High: {cls.format_currency(day_high)}
• Low: {cls.format_currency(day_low)}
• Prev Close: {cls.format_currency(prev_close)}

📊 **Volume:**
• Current: {cls.format_volume(volume)}
• Average: {cls.format_volume(avg_volume)}"""

            if volume and avg_volume:
                volume_ratio = (volume / avg_volume) * 100
                response += f"\n• Volume vs Avg: {volume_ratio:.0f}%"

            response += f"\n\n💰 **Market Cap:** {cls.format_currency(market_cap)}"

            response += f"\n\n📉 **52 Week Range:**"
            response += f"\n• Low: {cls.format_currency(week_52_low)}"
            response += f"\n• High: {cls.format_currency(week_52_high)}"
            
            if week_52_high and week_52_low:
                range_position = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100
                response += f"\n• Position: {range_position:.0f}% of range"

            if ma_50 or ma_200:
                response += f"\n\n📊 **Moving Averages:**"
                if ma_50:
                    ma_50_diff = ((current_price - ma_50) / ma_50) * 100
                    response += f"\n• 50-Day MA: {cls.format_currency(ma_50)} ({ma_50_diff:+.1f}%)"
                if ma_200:
                    ma_200_diff = ((current_price - ma_200) / ma_200) * 100
                    response += f"\n• 200-Day MA: {cls.format_currency(ma_200)} ({ma_200_diff:+.1f}%)"

            if pe_ratio or forward_pe or dividend_yield or beta:
                response += f"\n\n📈 **Fundamentals:**"
                if pe_ratio:
                    response += f"\n• P/E Ratio: {pe_ratio:.2f}"
                if forward_pe:
                    response += f"\n• Forward P/E: {forward_pe:.2f}"
                if dividend_yield:
                    response += f"\n• Dividend Yield: {dividend_yield*100:.2f}%"
                if beta:
                    response += f"\n• Beta: {beta:.2f}"

            # Add timestamp
            response += f"\n\n⏰ _Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
            
            return response
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {e}")
            return f"❌ Error fetching stock data for '{ticker}'. Please check the ticker symbol and try again."
    
    @classmethod
    async def get_market_summary(cls) -> str:
        """Get a summary of major market indices"""
        try:
            indices = {
                '^GSPC': 'S&P 500',
                '^DJI': 'Dow Jones',
                '^IXIC': 'NASDAQ',
                '^VIX': 'VIX (Volatility)',
                '^FTSE': 'FTSE 100',
                '^N225': 'Nikkei 225'
            }
            
            response = "🌍 **Global Market Summary**\n\n"
            
            for symbol, name in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2d")
                    
                    if not hist.empty and len(hist) >= 2:
                        current = hist['Close'].iloc[-1]
                        previous = hist['Close'].iloc[-2]
                        change_pct = ((current - previous) / previous) * 100
                        
                        response += f"**{name}:** {current:.2f} {cls.format_percentage(change_pct)}\n"
                except:
                    continue
            
            response += f"\n⏰ _Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
            return response
            
        except Exception as e:
            logger.error(f"Error fetching market summary: {e}")
            return "❌ Error fetching market summary. Please try again later."

# Create singleton instance
stock_tracker = StockTracker()
