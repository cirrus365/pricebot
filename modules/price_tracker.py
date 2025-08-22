"""Price tracking module for fiat and cryptocurrency rates"""
import aiohttp
import asyncio
import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

# Cache for exchange rates (5 minute TTL)
RATE_CACHE = {}
CACHE_TTL = 300  # 5 minutes

class PriceTracker:
    """Handles fetching and formatting price data"""
    
    # Fiat currency symbols
    FIAT_SYMBOLS = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 
        'CNY': '¥', 'INR': '₹', 'KRW': '₩', 'RUB': '₽',
        'CAD': 'C$', 'AUD': 'A$', 'CHF': 'Fr', 'SEK': 'kr',
        'NOK': 'kr', 'DKK': 'kr', 'PLN': 'zł', 'CZK': 'Kč',
        'NZD': 'NZ$', 'MXN': '$', 'BRL': 'R$', 'ZAR': 'R',
        'HKD': 'HK$', 'SGD': 'S$', 'THB': '฿', 'TRY': '₺'
    }
    
    # Common crypto symbols
    CRYPTO_SYMBOLS = {
        'BTC': 'bitcoin', 'ETH': 'ethereum', 'XMR': 'monero',
        'LTC': 'litecoin', 'DOGE': 'dogecoin', 'ADA': 'cardano',
        'DOT': 'polkadot', 'LINK': 'chainlink', 'UNI': 'uniswap',
        'SOL': 'solana', 'MATIC': 'polygon', 'AVAX': 'avalanche',
        'ATOM': 'cosmos', 'XRP': 'ripple', 'BNB': 'binancecoin'
    }
    
    # Common fiat currencies for validation
    COMMON_FIAT = {
        'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'KRW', 'RUB',
        'CAD', 'AUD', 'CHF', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK',
        'NZD', 'MXN', 'BRL', 'ZAR', 'HKD', 'SGD', 'THB', 'TRY',
        'ARS', 'CLP', 'COP', 'PEN', 'UYU', 'PHP', 'MYR', 'IDR'
    }
    
    @staticmethod
    def get_cache_key(from_currency: str, to_currency: str) -> str:
        """Generate cache key for rate pair"""
        return f"{from_currency.upper()}_{to_currency.upper()}"
    
    @staticmethod
    def is_cache_valid(cache_entry: dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        timestamp = cache_entry.get('timestamp')
        if not timestamp:
            return False
        return (datetime.now() - timestamp).seconds < CACHE_TTL
    
    @classmethod
    async def get_fiat_rate(cls, from_currency: str, to_currency: str) -> Optional[float]:
        """Get fiat exchange rate using Frankfurter API"""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Check cache
        cache_key = cls.get_cache_key(from_currency, to_currency)
        if cache_key in RATE_CACHE and cls.is_cache_valid(RATE_CACHE[cache_key]):
            return RATE_CACHE[cache_key]['rate']
        
        try:
            url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = data['rates'].get(to_currency)
                        if rate:
                            # Cache the result
                            RATE_CACHE[cache_key] = {
                                'rate': rate,
                                'timestamp': datetime.now()
                            }
                            return rate
        except Exception as e:
            print(f"Error fetching fiat rate from Frankfurter: {e}")
        
        # Fallback to ExchangeRate-API if Frankfurter fails
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = data['rates'].get(to_currency)
                        if rate:
                            # Cache the result
                            RATE_CACHE[cache_key] = {
                                'rate': rate,
                                'timestamp': datetime.now()
                            }
                            return rate
        except Exception as e:
            print(f"Error fetching fiat rate from ExchangeRate-API: {e}")
        
        return None
    
    @classmethod
    async def get_crypto_price(cls, crypto: str, fiat: str = 'USD') -> Optional[Dict]:
        """Get cryptocurrency price in fiat currency"""
        crypto = crypto.upper()
        fiat = fiat.upper()
        
        # Check cache
        cache_key = cls.get_cache_key(crypto, fiat)
        if cache_key in RATE_CACHE and cls.is_cache_valid(RATE_CACHE[cache_key]):
            return RATE_CACHE[cache_key]['data']
        
        # Get crypto ID for CoinGecko
        crypto_id = cls.CRYPTO_SYMBOLS.get(crypto, crypto.lower())
        
        # Try CoinGecko first
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies={fiat.lower()}&include_24hr_change=true&include_24hr_vol=true"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if crypto_id in data:
                            price_data = {
                                'price': data[crypto_id].get(fiat.lower()),
                                'change_24h': data[crypto_id].get(f'{fiat.lower()}_24h_change'),
                                'volume_24h': data[crypto_id].get(f'{fiat.lower()}_24h_vol')
                            }
                            # Cache the result
                            RATE_CACHE[cache_key] = {
                                'data': price_data,
                                'timestamp': datetime.now()
                            }
                            return price_data
        except Exception as e:
            print(f"Error fetching crypto price from CoinGecko: {e}")
        
        # Fallback to CoinCap
        try:
            # First get asset data
            url = f"https://api.coincap.io/v2/assets/{crypto_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            price_usd = float(data['data'].get('priceUsd', 0))
                            change_24h = float(data['data'].get('changePercent24Hr', 0))
                            volume_24h = float(data['data'].get('volumeUsd24Hr', 0))
                            
                            # Convert to requested fiat if not USD
                            if fiat != 'USD':
                                fiat_rate = await cls.get_fiat_rate('USD', fiat)
                                if fiat_rate:
                                    price_usd *= fiat_rate
                                    volume_24h *= fiat_rate
                            
                            price_data = {
                                'price': price_usd,
                                'change_24h': change_24h,
                                'volume_24h': volume_24h
                            }
                            # Cache the result
                            RATE_CACHE[cache_key] = {
                                'data': price_data,
                                'timestamp': datetime.now()
                            }
                            return price_data
        except Exception as e:
            print(f"Error fetching crypto price from CoinCap: {e}")
        
        return None
    
    @classmethod
    def format_price(cls, amount: float, currency: str) -> str:
        """Format price with appropriate symbol and decimals"""
        currency = currency.upper()
        symbol = cls.FIAT_SYMBOLS.get(currency, '')
        
        # Determine decimal places based on amount
        if amount < 0.01:
            decimals = 6
        elif amount < 1:
            decimals = 4
        elif amount < 100:
            decimals = 2
        else:
            decimals = 0
        
        formatted = f"{amount:,.{decimals}f}"
        
        # Handle currency symbol placement
        if symbol and currency in ['USD', 'GBP', 'EUR', 'INR', 'CAD', 'AUD', 'NZD', 'HKD', 'SGD', 'MXN', 'BRL', 'ZAR']:
            return f"{symbol}{formatted}"
        elif symbol:
            return f"{formatted} {symbol}"
        else:
            return f"{formatted} {currency}"
    
    @classmethod
    def format_percentage(cls, value: float) -> str:
        """Format percentage change with color indicators"""
        if value > 0:
            return f"📈 +{value:.2f}%"
        elif value < 0:
            return f"📉 {value:.2f}%"
        else:
            return f"➡️ {value:.2f}%"
    
    @classmethod
    async def parse_price_request(cls, message: str) -> Optional[Dict]:
        """Parse message for price requests"""
        message_lower = message.lower()
        
        # Patterns for crypto prices
        crypto_patterns = [
            r'\b([a-z]{2,5})\s+(?:to\s+)?([a-z]{3,4})\b',  # btc usd, xmr to eur
            r'\b([a-z]{2,5})\s+price\s+(?:in\s+)?([a-z]{3,4})?\b',  # btc price in usd
            r'price\s+(?:of\s+)?([a-z]{2,5})\s+(?:in\s+)?([a-z]{3,4})?\b',  # price of eth in eur
        ]
        
        # Check for crypto price requests
        for pattern in crypto_patterns:
            match = re.search(pattern, message_lower)
            if match:
                potential_crypto = match.group(1).upper()
                potential_fiat = match.group(2).upper() if match.group(2) else 'USD'
                
                # Check if it's a known crypto
                if potential_crypto in cls.CRYPTO_SYMBOLS or len(potential_crypto) <= 5:
                    # Verify it's likely a fiat currency for the second part
                    if potential_fiat in cls.COMMON_FIAT:
                        return {
                            'type': 'crypto',
                            'from': potential_crypto,
                            'to': potential_fiat
                        }
        
        # Patterns for fiat exchange rates with amounts
        fiat_amount_patterns = [
            r'(\d+(?:\.\d+)?)\s+([a-z]{3})\s+(?:to\s+|in\s+)?([a-z]{3})\b',  # 100 usd to eur
            r'convert\s+(\d+(?:\.\d+)?)\s+([a-z]{3})\s+(?:to\s+)?([a-z]{3})\b',  # convert 50 cad to aud
        ]
        
        for pattern in fiat_amount_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount = float(match.group(1))
                from_currency = match.group(2).upper()
                to_currency = match.group(3).upper()
                
                # Check if both are fiat currencies
                if from_currency in cls.COMMON_FIAT and to_currency in cls.COMMON_FIAT:
                    return {
                        'type': 'fiat',
                        'from': from_currency,
                        'to': to_currency,
                        'amount': amount
                    }
        
        # Patterns for fiat exchange rates without amounts
        fiat_patterns = [
            r'\b([a-z]{3})\s+(?:to\s+)?([a-z]{3})\b',  # usd to eur
            r'exchange\s+rate\s+([a-z]{3})\s+(?:to\s+)?([a-z]{3})\b',  # exchange rate usd to nzd
        ]
        
        for pattern in fiat_patterns:
            match = re.search(pattern, message_lower)
            if match:
                from_currency = match.group(1).upper()
                to_currency = match.group(2).upper() if len(match.groups()) > 1 else match.group(1).upper()
                
                # Check if both are fiat currencies
                if from_currency in cls.COMMON_FIAT and to_currency in cls.COMMON_FIAT:
                    return {
                        'type': 'fiat',
                        'from': from_currency,
                        'to': to_currency,
                        'amount': 1
                    }
        
        return None
    
    @classmethod
    async def get_price_response(cls, message: str) -> Optional[str]:
        """Get formatted price response for a message"""
        request = await cls.parse_price_request(message)
        if not request:
            return None
        
        if request['type'] == 'crypto':
            # Get crypto price
            price_data = await cls.get_crypto_price(request['from'], request['to'])
            if price_data and price_data['price']:
                response = f"💰 **{request['from']} Price**\n"
                response += f"Price: {cls.format_price(price_data['price'], request['to'])}\n"
                
                if price_data.get('change_24h') is not None:
                    response += f"24h Change: {cls.format_percentage(price_data['change_24h'])}\n"
                
                if price_data.get('volume_24h'):
                    volume_formatted = cls.format_price(price_data['volume_24h'], request['to'])
                    response += f"24h Volume: {volume_formatted}"
                
                return response
            else:
                return f"❌ Couldn't fetch price for {request['from']} in {request['to']}"
        
        elif request['type'] == 'fiat':
            # Get fiat exchange rate
            rate = await cls.get_fiat_rate(request['from'], request['to'])
            if rate:
                amount = request.get('amount', 1)
                converted = amount * rate
                
                response = f"💱 **Exchange Rate**\n"
                response += f"{cls.format_price(amount, request['from'])} = {cls.format_price(converted, request['to'])}\n"
                
                if amount != 1:
                    response += f"Rate: 1 {request['from']} = {cls.format_price(rate, request['to'])}"
                
                return response
            else:
                return f"❌ Couldn't fetch exchange rate for {request['from']} to {request['to']}"
        
        return None

# Create singleton instance
price_tracker = PriceTracker()
