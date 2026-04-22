"""
Pakistan Stock Analyst Agent
Powered by Google ADK + Gemini
"""

import os
import logging
import requests
import yfinance as yf
from dotenv import load_dotenv
from google.adk.agents import Agent
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# Tool: Get stock quote from Yahoo Finance (supports PSX tickers like ENGRO.KA)
# ---------------------------------------------------------------------------

def get_stock_quote(ticker: str) -> dict:
    """
    Fetch the current quote for a stock ticker from Yahoo Finance.
    For PSX (Pakistan Stock Exchange) stocks, append '.KA' to the ticker
    (e.g. 'ENGRO' → 'ENGRO.KA', 'OGDC' → 'OGDC.KA').
    Returns price, change, 52-week high/low, PE ratio, market cap, volume, and more.

    Args:
        ticker: The stock ticker symbol. For PSX stocks provide just the company
                symbol without '.KA' — the tool will add the suffix automatically.

    Returns:
        A dictionary with quote fields, or an error message.
    """
    # Normalise ticker: add .KA for PSX if not already suffixed
    ticker = ticker.strip().upper()
    psx_known = {
        "ENGRO", "OGDC", "PPL", "PSO", "LUCK", "HBL", "UBL", "MCB", "NBP",
        "MARI", "EFERT", "FFC", "HUBC", "KAPCO", "SEARL", "COLG", "NESTLE",
        "UNITY", "MLCF", "KOHC", "DGKC", "CHCC", "PIOC", "FCCL", "ACPL",
        "PKGS", "SNGP", "SSGC", "PTCL", "TRG", "SYSTEMS", "AVN", "NETSOL",
        "PAKT", "SHEL", "APL", "HASCOL", "MEBL", "BAHL", "FABL", "SILK",
        "AKBL", "JSBL", "BIPL", "SNBL", "SMBL", "BAFL", "KASB",
    }
    if "." not in ticker and ticker in psx_known:
        ticker = ticker + ".KA"
    elif "." not in ticker and not ticker.endswith(".KA"):
        # Assume PSX anyway
        ticker = ticker + ".KA"

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "1d"}
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        meta = data["chart"]["result"][0]["meta"]

        # --- Fetch correct price from yfinance history ---
        current_price = meta.get("regularMarketPrice")  # fallback default
        week52_high = meta.get("fiftyTwoWeekHigh")
        week52_low = meta.get("fiftyTwoWeekLow")

        try:
            yf_ticker = yf.Ticker(ticker)
            hist_5d = yf_ticker.history(period="5d")
            if not hist_5d.empty:
                current_price = round(float(hist_5d["Close"].iloc[-1]), 2)

            hist_1y = yf_ticker.history(period="1y")
            if not hist_1y.empty:
                week52_high = round(float(hist_1y["Close"].max()), 2)
                week52_low = round(float(hist_1y["Close"].min()), 2)
        except Exception as yf_err:
            logger.warning(
                "yfinance history failed for %s, falling back to chart API meta: %s",
                ticker, yf_err,
            )

        result = {
            "ticker": ticker,
            "company_name": meta.get("longName") or meta.get("shortName", ticker),
            "currency": meta.get("currency", "PKR"),
            "current_price": current_price,
            "previous_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
            "52_week_high": week52_high,
            "52_week_low": week52_low,
            "market_cap": meta.get("marketCap"),
            "exchange": meta.get("exchangeName", "PSX"),
        }

        # Calculate day change
        if result["current_price"] and result["previous_close"]:
            change = result["current_price"] - result["previous_close"]
            change_pct = (change / result["previous_close"]) * 100
            result["day_change"] = round(change, 2)
            result["day_change_pct"] = round(change_pct, 2)

        # Distance from 52-week high/low
        if result["current_price"] and result["52_week_high"] and result["52_week_low"]:
            price = result["current_price"]
            high = result["52_week_high"]
            low = result["52_week_low"]
            result["pct_from_52w_high"] = round(((price - high) / high) * 100, 2)
            result["pct_from_52w_low"] = round(((price - low) / low) * 100, 2)

        return result

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ---------------------------------------------------------------------------
# Tool: Get fundamental summary from Yahoo Finance summary page
# ---------------------------------------------------------------------------

def get_stock_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamental data for a stock: PE ratio, EPS, dividend yield,
    book value, price-to-book, profit margins, revenue, and analyst target price.
    For PSX stocks provide just the base symbol (e.g. 'ENGRO').

    Args:
        ticker: Stock ticker symbol (PSX base symbol or full Yahoo ticker).

    Returns:
        Dictionary with fundamental metrics.
    """
    ticker = ticker.strip().upper()
    if "." not in ticker:
        ticker = ticker + ".KA"

    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info

        # Calculate P/E manually using the correct PSX price
        hist = t.history(period="5d")
        price = hist["Close"].iloc[-1] if not hist.empty else None

        eps_ttm = info.get("trailingEps")
        pe_ratio_ttm = round(price / eps_ttm, 2) if price and eps_ttm and eps_ttm > 0 else None

        forward_eps = info.get("forwardEps")
        forward_pe = round(price / forward_eps, 2) if price and forward_eps and forward_eps > 0 else None

        return {
            "ticker": ticker,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "pe_ratio_ttm": pe_ratio_ttm,
            "forward_pe": forward_pe,
            "eps_ttm": eps_ttm,
            "price_to_book": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            "beta": info.get("beta"),
            "book_value_per_share": info.get("bookValue"),
            "revenue": info.get("totalRevenue"),
            "gross_margins": info.get("grossMargins"),
            "operating_margins": info.get("operatingMargins"),
            "profit_margins": info.get("profitMargins"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "analyst_target_price": info.get("targetMeanPrice"),
            "analyst_recommendation": info.get("recommendationKey"),
            "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ---------------------------------------------------------------------------
# Tool: Get recent news headlines for a company
# ---------------------------------------------------------------------------

def get_stock_news(company_name: str) -> dict:
    """
    Fetch recent news headlines about a company or PSX stock from Google News.

    Args:
        company_name: The company name or ticker (e.g. 'Engro', 'OGDC', 'Lucky Cement').

    Returns:
        Dictionary with a list of recent news headlines.
    """
    query = f"{company_name} Pakistan stock site:bloomberg.com OR site:dawn.com OR site:brecorder.com OR site:thenews.com.pk"
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(company_name + ' Pakistan stock')}&hl=en-PK&gl=PK&ceid=PK:en"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("item")[:8]

        headlines = []
        for item in items:
            headlines.append({
                "title": item.find("title").text if item.find("title") else "",
                "published": item.find("pubDate").text if item.find("pubDate") else "",
                "source": item.find("source").text if item.find("source") else "",
            })

        return {"company": company_name, "headlines": headlines}

    except Exception as e:
        return {"error": str(e), "company": company_name}


# ---------------------------------------------------------------------------
# Tool: Compare multiple stocks
# ---------------------------------------------------------------------------

def compare_stocks(tickers: list[str]) -> dict:
    """
    Compare key metrics across multiple PSX stocks side by side.
    Useful for sector comparisons or when evaluating alternatives.

    Args:
        tickers: List of PSX stock tickers (e.g. ['ENGRO', 'EFERT', 'FFC']).

    Returns:
        Dictionary with a comparison table of each stock's key metrics.
    """
    results = {}
    for ticker in tickers:
        quote = get_stock_quote(ticker)
        funds = get_stock_fundamentals(ticker)
        results[ticker.upper()] = {
            "price": quote.get("current_price"),
            "day_change_pct": quote.get("day_change_pct"),
            "52w_high": quote.get("52_week_high"),
            "52w_low": quote.get("52_week_low"),
            "pct_from_52w_high": quote.get("pct_from_52w_high"),
            "pe_ratio": funds.get("pe_ratio_ttm"),
            "eps": funds.get("eps_ttm"),
            "dividend_yield": funds.get("dividend_yield"),
            "profit_margin": funds.get("profit_margins"),
            "roe": funds.get("return_on_equity"),
            "analyst_target": funds.get("analyst_target_price"),
            "recommendation": funds.get("analyst_recommendation"),
        }
    return {"comparison": results}


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="stock_analyst_agent",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "An expert Pakistan Stock Exchange (PSX) analyst. "
        "Answers questions about stock valuations, financials, news, and "
        "provides data-driven buy/sell/hold recommendations."
    ),
    instruction="""
You are a highly experienced stock market analyst specializing in the Pakistan Stock Exchange (PSX).

Your capabilities:
- Fetch live stock quotes and price data
- Retrieve fundamental data (PE ratio, EPS, dividends, margins, ROE, etc.)
- Get recent news about companies
- Compare multiple stocks side-by-side

Your analysis approach:
1. Always fetch fresh data using your tools before giving opinions.
2. Provide structured, clear analysis with key metrics.
3. Consider both quantitative (PE, EPS, price trends) and qualitative factors (sector outlook, news).
4. Always state your data-driven reasoning transparently.
5. Use the following valuation framework for PSX:
   - PE < 8: Potentially undervalued (PSX historical avg is ~7-10)
   - PE 8-15: Fairly valued
   - PE > 15: Potentially overpriced (scrutinise carefully)
   - If stock is >20% below 52w high with strong fundamentals → possible opportunity
   - If stock is near 52w high with high PE → caution flag

6. When asked "is X overpriced/undervalued/good buy?":
   - First call get_stock_quote to get price context
   - Then call get_stock_fundamentals for valuation metrics
   - Optionally call get_stock_news for recent sentiment
   - Synthesize all data into a clear, professional verdict

7. Always mention Pakistan-specific factors: PKR depreciation, interest rates (SBP policy rate), inflation, sector-specific risks.

Format your responses with clear sections:
📊 **Price Overview** | 📈 **Valuation** | 💰 **Dividends & Returns** | 📰 **News Sentiment** | ✅ **Verdict**

Be confident, precise, and professional. If data is unavailable for a field, note it but continue the analysis.
""",
    tools=[
        get_stock_quote,
        get_stock_fundamentals,
        get_stock_news,
        compare_stocks,
    ],
)