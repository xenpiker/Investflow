#!/usr/bin/env python3
"""
InvestFlow Backend Server
Fetches real stock data from Alpha Vantage API
"""
import http.server
import socketserver
import json
import urllib.request
import urllib.parse
import ssl

PORT = 8084
ALPHA_VANTAGE_API_KEY = "54SEVFPL3DI7LR6K"

# Simple in-memory cache (30 seconds)
CACHE = {}
CACHE_TTL = 30

class InvestFlowHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/stock/'):
            ticker = self.path.split('/api/stock/')[1].strip('/').upper()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                data = self.fetch_stock_data(ticker)
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        
        # Serve static files
        return super().do_GET()
    
    def fetch_stock_data(self, ticker):
        import time
        
        # Check cache
        cache_key = ticker
        if cache_key in CACHE:
            cached_data, cached_time = CACHE[cache_key]
            if time.time() - cached_time < CACHE_TTL:
                return cached_data
        
        # Get GLOBAL QUOTE (price data)
        quote_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
        quote_data = self.fetch_json(quote_url)
        
        if 'Global Quote' not in quote_data or not quote_data['Global Quote']:
            raise Exception(f"Stock {ticker} not found or API rate limited")
        
        q = quote_data['Global Quote']
        
        # Get company overview
        overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
        overview = self.fetch_json(overview_url)
        
        return {
            'ticker': ticker,
            'name': overview.get('Name', ticker),
            'price': float(q.get('05. price', 0)),
            'change': float(q.get('09. change', 0)),
            'changePct': float(q.get('10. change percent', '0').replace('%', '')),
            'volume': int(q.get('06. volume', 0)),
            'open': float(q.get('02. open', 0)),
            'high': float(q.get('03. high', 0)),
            'low': float(q.get('04. low', 0)),
            'previousClose': float(q.get('08. previous close', 0)),
            'marketCap': overview.get('MarketCapitalization', 0),
            'pe': overview.get('PERatio', None),
            'eps': overview.get('EPS', None),
            'dividendYield': overview.get('DividendYield', None),
            'beta': overview.get('Beta', None),
            'sector': overview.get('Sector', 'Unknown'),
            'industry': overview.get('Industry', 'Unknown'),
            'description': overview.get('Description', ''),
            'revenue': overview.get('RevenueTTM', 0),
            'profitMargin': overview.get('ProfitMargin', 0),
            'operatingMargin': overview.get('OperatingMargin', 0),
            'grossMargin': overview.get('GrossMarginTTM', 0),
            'evEbitda': overview.get('EVToEBITDA', None),
            'peg': overview.get('PEGRatio', None),
        }
        
        # Save to cache
        CACHE[cache_key] = (result, time.time())
        return result
    
    def fetch_json(self, url):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
            })
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"Error fetching: {e}")
            return {}

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), InvestFlowHandler) as httpd:
        print(f"InvestFlow server running at http://localhost:{PORT}")
        print(f"Stock data API: http://localhost:{PORT}/api/stock/{{ticker}}")
        httpd.serve_forever()