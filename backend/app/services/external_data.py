"""External data APIs: News, Weather, Stocks."""

import httpx
from typing import List, Dict, Optional
from datetime import datetime, timezone
from app.config import settings


class NewsAPIService:
    """
    News API service for fetching news articles.
    Free tier: 100 requests/day
    Get API key: https://newsapi.org/
    """

    def __init__(self):
        self.base_url = "https://newsapi.org/v2"
        self.api_key = getattr(settings, 'newsapi_key', None)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_top_headlines(
        self,
        query: Optional[str] = None,
        category: str = "technology",
        country: str = "us",
        max_results: int = 5
    ) -> List[Dict]:
        """Get top headlines."""
        if not self.is_configured():
            return []

        params = {
            "apiKey": self.api_key,
            "category": category,
            "country": country,
            "pageSize": max_results,
        }
        if query:
            params["q"] = query

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/top-headlines",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                articles = []
                for article in data.get("articles", []):
                    articles.append({
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "content": article.get("content", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "published_at": article.get("publishedAt", ""),
                        "image_url": article.get("urlToImage"),
                    })

                return articles

        except Exception as e:
            print(f"NewsAPI error: {e}")
            return []

    async def search_news(
        self,
        query: str,
        from_date: Optional[str] = None,
        sort_by: str = "relevancy",
        max_results: int = 5
    ) -> List[Dict]:
        """Search all news articles."""
        if not self.is_configured():
            return []

        params = {
            "apiKey": self.api_key,
            "q": query,
            "sortBy": sort_by,
            "pageSize": max_results,
            "language": "en",
        }
        if from_date:
            params["from"] = from_date

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/everything",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "title": a.get("title", ""),
                        "description": a.get("description", ""),
                        "content": a.get("content", ""),
                        "url": a.get("url", ""),
                        "source": a.get("source", {}).get("name", ""),
                        "published_at": a.get("publishedAt", ""),
                    }
                    for a in data.get("articles", [])
                ]

        except Exception as e:
            print(f"NewsAPI search error: {e}")
            return []


class WeatherService:
    """
    OpenWeatherMap service for weather data.
    Free tier: 1000 calls/day
    Get API key: https://openweathermap.org/api
    """

    def __init__(self):
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.api_key = getattr(settings, 'openweather_api_key', None)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_current_weather(
        self,
        city: str,
        units: str = "metric"
    ) -> Optional[Dict]:
        """Get current weather for a city."""
        if not self.is_configured():
            return None

        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "city": data.get("name", city),
                    "country": data.get("sys", {}).get("country", ""),
                    "temperature": data.get("main", {}).get("temp"),
                    "feels_like": data.get("main", {}).get("feels_like"),
                    "humidity": data.get("main", {}).get("humidity"),
                    "description": data.get("weather", [{}])[0].get("description", ""),
                    "wind_speed": data.get("wind", {}).get("speed"),
                    "clouds": data.get("clouds", {}).get("all"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            print(f"Weather API error: {e}")
            return None

    async def get_forecast(
        self,
        city: str,
        days: int = 5,
        units: str = "metric"
    ) -> List[Dict]:
        """Get weather forecast."""
        if not self.is_configured():
            return []

        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
            "cnt": days * 8,  # 3-hour intervals
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                forecasts = []
                for item in data.get("list", []):
                    forecasts.append({
                        "datetime": item.get("dt_txt", ""),
                        "temperature": item.get("main", {}).get("temp"),
                        "description": item.get("weather", [{}])[0].get("description", ""),
                        "humidity": item.get("main", {}).get("humidity"),
                        "wind_speed": item.get("wind", {}).get("speed"),
                    })

                return forecasts

        except Exception as e:
            print(f"Weather forecast error: {e}")
            return []


class StockService:
    """
    Alpha Vantage service for stock market data.
    Free tier: 25 requests/day
    Get API key: https://www.alphavantage.co/
    """

    def __init__(self):
        self.base_url = "https://www.alphavantage.co/query"
        self.api_key = getattr(settings, 'alphavantage_api_key', None)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time stock quote."""
        if not self.is_configured():
            return None

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

                quote = data.get("Global Quote", {})
                if not quote:
                    return None

                return {
                    "symbol": quote.get("01. symbol", symbol),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%"),
                    "volume": int(quote.get("06. volume", 0)),
                    "latest_trading_day": quote.get("07. latest trading day", ""),
                    "previous_close": float(quote.get("08. previous close", 0)),
                    "open": float(quote.get("02. open", 0)),
                    "high": float(quote.get("03. high", 0)),
                    "low": float(quote.get("04. low", 0)),
                }

        except Exception as e:
            print(f"Stock quote error: {e}")
            return None

    async def search_symbol(self, keywords: str) -> List[Dict]:
        """Search for stock symbols."""
        if not self.is_configured():
            return []

        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
            "apikey": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

                matches = []
                for match in data.get("bestMatches", []):
                    matches.append({
                        "symbol": match.get("1. symbol", ""),
                        "name": match.get("2. name", ""),
                        "type": match.get("3. type", ""),
                        "region": match.get("4. region", ""),
                        "currency": match.get("8. currency", ""),
                    })

                return matches

        except Exception as e:
            print(f"Symbol search error: {e}")
            return []

    async def get_company_overview(self, symbol: str) -> Optional[Dict]:
        """Get company overview and fundamentals."""
        if not self.is_configured():
            return None

        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data or "Symbol" not in data:
                    return None

                return {
                    "symbol": data.get("Symbol", symbol),
                    "name": data.get("Name", ""),
                    "description": data.get("Description", ""),
                    "sector": data.get("Sector", ""),
                    "industry": data.get("Industry", ""),
                    "market_cap": data.get("MarketCapitalization", ""),
                    "pe_ratio": data.get("PERatio", ""),
                    "dividend_yield": data.get("DividendYield", ""),
                    "52_week_high": data.get("52WeekHigh", ""),
                    "52_week_low": data.get("52WeekLow", ""),
                }

        except Exception as e:
            print(f"Company overview error: {e}")
            return None


# Singleton instances
news_service = NewsAPIService()
weather_service = WeatherService()
stock_service = StockService()
