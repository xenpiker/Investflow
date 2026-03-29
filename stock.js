// Vercel API route for stock data
const ALPHA_VANTAGE_API_KEY = process.env.ALPHA_VANTAGE_API_KEY || "54SEVFPL3DI7LR6K";

// Simple in-memory cache (30 seconds)
const cache = new Map();

export default async function handler(req, res) {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Content-Type', 'application/json');
    
    if (req.method !== 'GET') {
        return res.status(405).json({ error: 'Method not allowed' });
    }
    
    // Parse ticker from query
    const ticker = req.query.ticker?.toUpperCase();
    if (!ticker) {
        return res.status(400).json({ error: 'Ticker is required' });
    }
    
    // Check cache
    const cacheKey = ticker;
    if (cache.has(cacheKey)) {
        const cached = cache.get(cacheKey);
        if (Date.now() - cached.timestamp < 30000) {
            return res.status(200).json(cached.data);
        }
    }
    
    try {
        // Fetch quote data
        const quoteUrl = `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${ticker}&apikey=${ALPHA_VANTAGE_API_KEY}`;
        const quoteRes = await fetch(quoteUrl);
        const quoteData = await quoteRes.json();
        
        if (!quoteData['Global Quote'] || !quoteData['Global Quote']['05. price']) {
            return res.status(404).json({ error: `Stock ${ticker} not found` });
        }
        
        const q = quoteData['Global Quote'];
        
        // Fetch company overview (separate call, may fail due to rate limits)
        let overview = {};
        try {
            const overviewUrl = `https://www.alphavantage.co/query?function=OVERVIEW&symbol=${ticker}&apikey=${ALPHA_VANTAGE_API_KEY}`;
            const overviewRes = await fetch(overviewUrl);
            overview = await overviewRes.json();
        } catch (e) {
            console.log('Overview fetch failed, continuing without');
        }
        
        const result = {
            ticker,
            name: overview.Name || ticker,
            price: parseFloat(q['05. price']),
            change: parseFloat(q['09. change']),
            changePct: parseFloat(q['10. change percent']?.replace('%', '') || 0),
            volume: parseInt(q['06. volume']),
            open: parseFloat(q['02. open']),
            high: parseFloat(q['03. high']),
            low: parseFloat(q['04. low']),
            previousClose: parseFloat(q['08. previous close']),
            marketCap: overview.MarketCapitalization || 0,
            pe: overview.PERatio || null,
            eps: overview.EPS || null,
            dividendYield: overview.DividendYield || null,
            beta: overview.Beta || null,
            sector: overview.Sector || 'Unknown',
            industry: overview.Industry || 'Unknown',
            description: overview.Description || '',
            revenue: overview.RevenueTTM || 0,
            profitMargin: overview.ProfitMargin || 0,
            operatingMargin: overview.OperatingMargin || 0,
            grossMargin: overview.GrossMarginTTM || 0,
            evEbitda: overview.EVToEBITDA || null,
            peg: overview.PEGRatio || null,
        };
        
        // Cache result
        cache.set(cacheKey, { data: result, timestamp: Date.now() });
        
        return res.status(200).json(result);
    } catch (error) {
        console.error('Stock API error:', error);
        return res.status(500).json({ error: error.message });
    }
}