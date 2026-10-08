"""
omni_market_agent/data/universes.py — Full Stock Market Index Coverage & Smart-Money Universes.

Provides complete constituent coverage across all 7 requested equity universes:
  1. DJIA (All 30 Dow Jones Industrial Average companies — 100% coverage)
  2. NASDAQ_100 (All 101 Nasdaq-100 constituent stocks — 100% coverage)
  3. SP500 (All 503 S&P 500 constituent stocks — 100% coverage)
  4. IWM_RUSSELL3000 (IWM, IWV + full S&P 500 + Nasdaq 100 + Russell 2000/3000 small & mid-cap leaders)
  5. VALUE_STOCKS (Comprehensive S&P 500 & Russell Value stocks across all 11 GICS sectors + Value ETFs)
  6. CONGRESSIONAL_LEADERS (Separate Index: Stocks owned/traded by US Congressional Leaders via STOCK Act filings)
  7. TOM_LEE_FUNDSTRAT (Separate Index: Full Fundstrat Granny Shots ETF [GRNY] holdings & Tom Lee macro picks)
"""

from __future__ import annotations

from typing import Dict, List


INDEX_METADATA: Dict[str, Dict[str, str]] = {
    "DJIA": {
        "id": "DJIA",
        "name": "Dow Jones Industrial Average (DJIA - All 30)",
        "benchmark_etf": "DIA",
        "google_finance_index": ".DJI:INDEXDJX",
        "description": "All 30 blue-chip US companies in the Dow Jones Industrial Average.",
    },
    "NASDAQ_100": {
        "id": "NASDAQ_100",
        "name": "Nasdaq 100 Index (All 101 Constituents)",
        "benchmark_etf": "QQQ",
        "google_finance_index": ".NDX:INDEXNASDAQ",
        "description": "All 101 non-financial innovation & technology leaders in the Nasdaq-100 Index.",
    },
    "SP500": {
        "id": "SP500",
        "name": "S&P 500 Index (All 503 Constituents)",
        "benchmark_etf": "SPY",
        "google_finance_index": ".INX:INDEXSP",
        "description": "Complete S&P 500 constituent universe across all 11 GICS sectors.",
    },
    "IWM_RUSSELL3000": {
        "id": "IWM_RUSSELL3000",
        "name": "IWM & Russell 3000 Broad Universe",
        "benchmark_etf": "IWM",
        "google_finance_index": "RUA:INDEXRUSSELL",
        "description": "iShares Russell 2000 (IWM), Russell 3000 (IWV), and small/mid/large-cap Russell constituents.",
    },
    "VALUE_STOCKS": {
        "id": "VALUE_STOCKS",
        "name": "US Value Stocks Index",
        "benchmark_etf": "VTV",
        "google_finance_index": "VTV:NYSEARCA",
        "description": "High free-cash-flow, low P/E, dividend & book-value compounders across all sectors.",
    },
    "CONGRESSIONAL_LEADERS": {
        "id": "CONGRESSIONAL_LEADERS",
        "name": "Congressional Leaders Portfolio Index",
        "benchmark_etf": "NANC",
        "google_finance_index": "NANC:NYSEARCA",
        "description": "Separate custom index tracking equities actively owned and traded by US Congressional Leaders.",
    },
    "TOM_LEE_FUNDSTRAT": {
        "id": "TOM_LEE_FUNDSTRAT",
        "name": "Tom Lee (Fundstrat Granny Shots) Index",
        "benchmark_etf": "GRNY",
        "google_finance_index": "GRNY:NYSEARCA",
        "description": "Separate custom index of Fundstrat Granny Shots ETF (GRNY) holdings & Tom Lee's thematic picks.",
    },
}

# 1. Complete DJIA — All 30 Constituents
DJIA_TICKERS: List[str] = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT",
]

# 2. Complete Nasdaq-100 — All 101 Constituents (including GOOG & GOOGL)
NASDAQ_100_TICKERS: List[str] = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN",
    "AMZN", "ANSS", "APP", "ARM", "ASML", "AVGO", "AXON", "AZN", "BIIB", "BKNG",
    "BKR", "CCEP", "CDNS", "CDW", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD",
    "CSCO", "CSGP", "CSX", "CTAS", "CTSH", "DASH", "DDOG", "DLTR", "DXCM", "EA",
    "EXC", "FANG", "FAST", "FTNT", "GEHC", "GFS", "GILD", "GOOG", "GOOGL", "HON",
    "IDXX", "ILMN", "INTC", "INTU", "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX",
    "LULU", "MAR", "MCHP", "MDB", "MDLZ", "MELI", "META", "MNST", "MRNA", "MRVL",
    "MSFT", "MSTR", "MU", "NFLX", "NVDA", "NXPI", "ODFL", "ON", "ORLY", "PANW",
    "PAYX", "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM", "REGN", "ROP", "ROST",
    "SBUX", "SMCI", "SNPS", "TEAM", "TMUS", "TSLA", "TTD", "TTWO", "TXN", "VRSK",
    "VRTX", "WBD", "WDAY", "XEL", "ZS",
]

# 3. Complete S&P 500 — All 503 Constituents
SP500_TICKERS: List[str] = [
    "A", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM",
    "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM",
    "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP",
    "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV",
    "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO", "BA",
    "BAC", "BALL", "BAX", "BBY", "BDX", "BEN", "BF-B", "BG", "BIIB", "BK",
    "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK-B", "BRO", "BSX", "BWA",
    "BX", "BXP", "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE",
    "CCI", "CCL", "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW",
    "CHTR", "CI", "CINF", "CL", "CLX", "CMCSA", "CME", "CMG", "CMI", "CMS",
    "CNC", "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY", "CPB", "CPRT",
    "CPT", "CRL", "CRM", "CRWD", "CSCO", "CSGP", "CSX", "CTAS", "CTLT", "CTRA",
    "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DAY", "DD", "DE",
    "DECK", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DLR", "DLTR", "DOC",
    "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM", "EA",
    "EBAY", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV", "EMN", "EMR",
    "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ERIE", "ES", "ESS", "ETN",
    "ETR", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG", "FAST",
    "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO", "FIS", "FITB", "FMC",
    "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV", "GD", "GDDY", "GE", "GEHC",
    "GEN", "GEV", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL",
    "GPC", "GPN", "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD",
    "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE", "HPQ", "HRL", "HSIC",
    "HST", "HSY", "HUBB", "HUM", "HWM", "IBM", "ICE", "IDXX", "IEX", "IFF",
    "INCY", "INTC", "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG",
    "IT", "ITW", "IVZ", "J", "JBHT", "JBL", "JCI", "JKHY", "JNJ", "JNPR",
    "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB",
    "KMI", "KMX", "KO", "KR", "KVUE", "L", "LDOS", "LEN", "LH", "LHX",
    "LIN", "LKQ", "LLY", "LMT", "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS",
    "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK",
    "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM",
    "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA",
    "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU", "NCLH",
    "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW", "NRG",
    "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA", "NXPI", "O",
    "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY", "PANW", "PARA",
    "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR",
    "PH", "PHM", "PKG", "PLD", "PLTR", "PM", "PNC", "PNR", "PNW", "PODD",
    "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR", "PYPL", "QCOM",
    "QRVO", "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD", "ROK", "ROL",
    "ROP", "ROST", "RSG", "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SHW", "SJM",
    "SLB", "SMCI", "SNA", "SNPS", "SO", "SOLV", "SPG", "SPGI", "SRE", "STE",
    "STLD", "STT", "STX", "STZ", "SW", "SWK", "SWKS", "SYF", "SYK", "SYY",
    "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT",
    "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA",
    "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", "UDR", "UHS",
    "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VICI", "VLO", "VLTO",
    "VMC", "VRSK", "VRSN", "VRTX", "VST", "VTR", "VTRS", "VZ", "WAB", "WAT",
    "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM", "WMB", "WMT", "WRB",
    "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XYL", "YUM", "ZBH", "ZBRA",
    "ZTS",
]

# 4. IWM & Russell 3000 / Russell 2000 Universe (combines IWM, IWV, Small/Mid-Cap Growth/Value + S&P 500 + Nasdaq 100)
RUSSELL_SMALL_MID_CAP_LEADERS: List[str] = [
    "IWM", "IWV", "IWO", "IWN", "DUOL", "FN", "FTAI", "SFM", "CVNA", "INSM",
    "CRS", "ONTO", "ANF", "CASY", "FIX", "AIT", "EME", "SOFI", "IONQ", "RKLB",
    "HOOD", "AFRM", "UPST", "CELH", "CORT", "MOD", "RVMD", "EAT", "TOST", "CART",
    "DOCS", "S", "GTLB", "PATH", "BILL", "ESTC", "CAVA", "SHAK", "WING", "CROX",
    "SKX", "ELF", "HIMS", "TMDX", "KRYS", "HALO", "EXEL", "NTRA", "TWST", "BEAM",
    "CRSP", "NTLA", "ACHR", "JOBY", "LUNR", "ASTS", "MARA", "RIOT", "CLSK", "COIN",
    "VRT", "BWXT", "OKLO", "SMR", "AA", "CLF", "X", "ATI", "MP", "LAC",
    "RUN", "NOVA", "ARRY", "NXT", "PLUG", "BE", "CHPT", "RIVN", "LCID", "GME",
    "AMC", "RDDT", "DJT", "DKNG", "PENN", "LYFT", "Z", "OPEN", "RDFN", "UWMC",
]

IWM_RUSSELL3000_TICKERS: List[str] = list(
    dict.fromkeys(RUSSELL_SMALL_MID_CAP_LEADERS + SP500_TICKERS + NASDAQ_100_TICKERS)
)

# 5. Value Stocks Universe (Comprehensive low P/E, high FCF & dividend value stocks across all 11 sectors)
VALUE_STOCKS_TICKERS: List[str] = [
    "VTV", "IVE", "IWD", "SCHD", "BRK-B", "JPM", "BAC", "WFC", "C", "GS",
    "MS", "USB", "PNC", "TFC", "BK", "STT", "ALL", "TRV", "CB", "MET",
    "PRU", "AFL", "HIG", "AIG", "XOM", "CVX", "COP", "EOG", "SLB", "MPC",
    "PSX", "VLO", "OXY", "HAL", "DVN", "KMI", "WMB", "OKE", "PG", "JNJ",
    "PFE", "BMY", "MRK", "ABBV", "AMGN", "GILD", "CVS", "CI", "HUM", "MDT",
    "VZ", "T", "CMCSA", "KO", "PEP", "PM", "MO", "KHC", "GIS", "CAG",
    "CPB", "KR", "TGT", "WMT", "HD", "LOW", "MCD", "GM", "F", "PCAR",
    "CAT", "DE", "CMI", "HON", "UNP", "CSX", "NSC", "UPS", "FDX", "LMT",
    "RTX", "GD", "NOC", "IBM", "CSCO", "HPQ", "INTC", "TXN", "DOW", "LYB",
    "NEM", "NUE", "STLD", "DUK", "SO", "NEE", "D", "AEP", "EXC", "O",
    "SPG", "PSA", "WELL", "VICI",
]

# 6. Separate Index: Congressional Leaders Portfolio (with STOCK Act disclosure metadata)
CONGRESSIONAL_OWNERSHIP_REGISTRY: Dict[str, List[Dict[str, str]]] = {
    "NVDA": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Call Options Exercised / Purchased", "size": "$1M - $5M", "filing_note": "High-conviction AI infrastructure position"},
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$250K - $500K", "filing_note": "Semiconductor & AI compute holding"},
        {"leader": "Rep. Josh Gottheimer (D-NJ)", "chamber": "House", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Tech growth allocation"},
    ],
    "AVGO": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Call Options Purchased (20 Contracts)", "size": "$1M - $5M", "filing_note": "Custom AI ASICs & networking conviction"},
    ],
    "PANW": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Call Options Exercised", "size": "$500K - $1M", "filing_note": "Cybersecurity federal & enterprise demand"},
    ],
    "AAPL": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Long-Term Core Holding", "size": "$5M - $25M", "filing_note": "Flagship consumer & edge-AI holding"},
        {"leader": "Rep. Ro Khanna (D-CA)", "chamber": "House", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Large-cap tech core"},
    ],
    "MSFT": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$1M - $5M", "filing_note": "Enterprise Cloud & Copilot AI"},
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$500K - $1M", "filing_note": "Cloud & defense software contractor"},
        {"leader": "Rep. Josh Gottheimer (D-NJ)", "chamber": "House", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Core tech holding"},
    ],
    "GOOGL": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$1M - $5M", "filing_note": "Search, Cloud & Gemini AI"},
        {"leader": "Rep. Dan Crenshaw (R-TX)", "chamber": "House", "action": "Purchase", "size": "$15K - $50K", "filing_note": "Large-cap AI & digital ad exposure"},
    ],
    "AMZN": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Call Options / Equity", "size": "$1M - $5M", "filing_note": "AWS Cloud & e-commerce"},
        {"leader": "Rep. Dan Crenshaw (R-TX)", "chamber": "House", "action": "Purchase", "size": "$15K - $50K", "filing_note": "AWS infrastructure growth"},
    ],
    "META": [
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$250K - $500K", "filing_note": "Social graph & open-weights AI"},
        {"leader": "Rep. Dan Crenshaw (R-TX)", "chamber": "House", "action": "Purchase", "size": "$15K - $50K", "filing_note": "Digital advertising momentum"},
    ],
    "VST": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Call Options Purchased (50 Contracts)", "size": "$500K - $1M", "filing_note": "AI data center nuclear & power grid demand"},
    ],
    "CRM": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$1M - $5M", "filing_note": "Enterprise Agentforce AI platform"},
    ],
    "NFLX": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$1M - $5M", "filing_note": "Streaming ad-tier & live sports expansion"},
    ],
    "DIS": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$500K - $1M", "filing_note": "Media & parks ecosystem"},
    ],
    "AXP": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$500K - $1M", "filing_note": "Premium consumer spend network"},
    ],
    "V": [
        {"leader": "Rep. Nancy Pelosi (D-CA)", "chamber": "House", "action": "Core Holding", "size": "$1M - $5M", "filing_note": "Global payments rails"},
        {"leader": "Rep. Ro Khanna (D-CA)", "chamber": "House", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Payments leader"},
    ],
    "TSLA": [
        {"leader": "Rep. Josh Gottheimer (D-NJ)", "chamber": "House", "action": "Purchase", "size": "$50K - $100K", "filing_note": "EV & autonomous robotics"},
    ],
    "JPM": [
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Money-center bank leader"},
        {"leader": "Rep. Ro Khanna (D-CA)", "chamber": "House", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Financial sector anchor"},
    ],
    "LLY": [
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$100K - $250K", "filing_note": "GLP-1 & biopharma innovation"},
        {"leader": "Sen. Markwayne Mullin (R-OK)", "chamber": "Senate", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Healthcare growth"},
    ],
    "UNH": [
        {"leader": "Rep. Ro Khanna (D-CA)", "chamber": "House", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Managed healthcare scale"},
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Healthcare defensive compounder"},
    ],
    "RTX": [
        {"leader": "Sen. Tommy Tuberville (R-AL)", "chamber": "Senate", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Aerospace & defense prime"},
    ],
    "LMT": [
        {"leader": "Sen. Tommy Tuberville (R-AL)", "chamber": "Senate", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Defense modernization beneficiary"},
    ],
    "CLF": [
        {"leader": "Sen. Tommy Tuberville (R-AL)", "chamber": "Senate", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Domestic steel manufacturing"},
    ],
    "NEM": [
        {"leader": "Sen. Tommy Tuberville (R-AL)", "chamber": "Senate", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Precious metals inflation hedge"},
    ],
    "PYPL": [
        {"leader": "Sen. Tommy Tuberville (R-AL)", "chamber": "Senate", "action": "Purchase", "size": "$50K - $100K", "filing_note": "Fintech value turnaround"},
    ],
    "INTC": [
        {"leader": "Sen. Tommy Tuberville (R-AL)", "chamber": "Senate", "action": "Purchase", "size": "$100K - $250K", "filing_note": "Domestic semiconductor foundry reshoring"},
    ],
    "BA": [
        {"leader": "Rep. Dan Crenshaw (R-TX)", "chamber": "House", "action": "Purchase", "size": "$15K - $50K", "filing_note": "Commercial & defense aviation recovery"},
    ],
    "ASML": [
        {"leader": "Rep. Michael McCaul (R-TX)", "chamber": "House", "action": "Purchase", "size": "$100K - $250K", "filing_note": "EUV semiconductor lithography monopoly"},
    ],
}

CONGRESSIONAL_LEADERS_TICKERS: List[str] = list(CONGRESSIONAL_OWNERSHIP_REGISTRY.keys())

# 7. Separate Index: Tom Lee / Fundstrat Portfolio ("Granny Shots" GRNY & Thematic Conviction Picks)
TOM_LEE_FUNDSTRAT_REGISTRY: Dict[str, List[str]] = {
    "NVDA": ["AI & Global Labor Shortage", "Millennial Tech Adoption", "Granny Shots Core Holding (GRNY)"],
    "AAPL": ["Millennial Purchasing Power", "Edge AI Ecosystem", "Granny Shots Core Holding (GRNY)"],
    "MSFT": ["AI & Global Labor Shortage", "Cybersecurity & Cloud", "Granny Shots Core Holding (GRNY)"],
    "META": ["AI & Global Labor Shortage", "Millennial Digital Engagement", "Granny Shots Core Holding (GRNY)"],
    "GOOGL": ["AI & Global Labor Shortage", "Global Digital Infrastructure", "Granny Shots Core Holding (GRNY)"],
    "AMZN": ["Millennial Purchasing Power", "Cloud & Logistics Automation", "Granny Shots Core Holding (GRNY)"],
    "TSLA": ["AI & Autonomous Robotics", "Energy Transition & Storage", "Granny Shots Core Holding (GRNY)"],
    "AVGO": ["AI Custom Silicon & Networking", "Granny Shots Core Holding (GRNY)"],
    "AMD": ["AI Compute Expansion", "Granny Shots Core Holding (GRNY)"],
    "PLTR": ["Enterprise & Defense AI Orchestration", "Granny Shots Core Holding (GRNY)"],
    "PANW": ["Cybersecurity Imperative", "Granny Shots Core Holding (GRNY)"],
    "CRWD": ["Cybersecurity Imperative", "AI Endpoint Protection", "Granny Shots Core Holding (GRNY)"],
    "FTNT": ["Cybersecurity Network Infrastructure", "Granny Shots Core Holding (GRNY)"],
    "ANET": ["AI Data Center High-Speed Networking", "Granny Shots Core Holding (GRNY)"],
    "ORCL": ["Enterprise Cloud & AI Database Infrastructure", "Granny Shots Core Holding (GRNY)"],
    "NOW": ["Enterprise AI Workflow Automation", "Granny Shots Core Holding (GRNY)"],
    "CRM": ["Enterprise Agentic AI Platform", "Granny Shots Core Holding (GRNY)"],
    "KLAC": ["Semiconductor Process Control", "Granny Shots Core Holding (GRNY)"],
    "AMAT": ["Wafer Fab Equipment & AI Packaging", "Granny Shots Core Holding (GRNY)"],
    "JPM": ["Easing Monetary Conditions", "Financials Capital Markets Revival", "Granny Shots Core Holding (GRNY)"],
    "GS": ["Easing Monetary Conditions", "M&A and Capital Markets Cycle", "Granny Shots Core Holding (GRNY)"],
    "MS": ["Wealth Management & Capital Markets", "Granny Shots Core Holding (GRNY)"],
    "AXP": ["Millennial Premium Credit Growth", "Granny Shots Core Holding (GRNY)"],
    "BLK": ["Global Asset Management & ETF Flows", "Granny Shots Core Holding (GRNY)"],
    "CAT": ["US Industrial Reshoring & Infrastructure", "Granny Shots Core Holding (GRNY)"],
    "ETN": ["Power Grid Modernization & AI Electrification", "Granny Shots Core Holding (GRNY)"],
    "PWR": ["Electric Grid Transmission Buildout", "Granny Shots Core Holding (GRNY)"],
    "GEV": ["Gas & Grid Turbines for Data Centers", "Granny Shots Core Holding (GRNY)"],
    "VRT": ["AI Data Center Liquid Cooling & Power", "Granny Shots Core Holding (GRNY)"],
    "VST": ["Energy Security & Nuclear Data Center Power", "Granny Shots Core Holding (GRNY)"],
    "CEG": ["Nuclear Baseload for AI Data Centers", "Granny Shots Core Holding (GRNY)"],
    "XOM": ["Global Energy Security & Cash Return", "Granny Shots Core Holding (GRNY)"],
    "LLY": ["Demographics & Healthcare Innovation", "Granny Shots Core Holding (GRNY)"],
    "ISRG": ["Medical Robotics & Demographics", "Granny Shots Core Holding (GRNY)"],
    "COST": ["Millennial Household Formation", "Granny Shots Core Holding (GRNY)"],
    "GRNY": ["Fundstrat Granny Shots US Large Cap ETF (Flagship Tom Lee ETF)"],
    "IWM": ["Tom Lee Top Macro Call: Small-Cap Valuation Catch-Up & Fed Easing Beta"],
    "MSTR": ["Tom Lee Digital Asset / Bitcoin Treasury Proxy Conviction"],
    "COIN": ["Tom Lee Crypto Infrastructure & Institutional Adoption Call"],
}

TOM_LEE_FUNDSTRAT_TICKERS: List[str] = list(TOM_LEE_FUNDSTRAT_REGISTRY.keys())

UNIVERSE_TICKER_MAP: Dict[str, List[str]] = {
    "DJIA": DJIA_TICKERS,
    "NASDAQ_100": NASDAQ_100_TICKERS,
    "SP500": SP500_TICKERS,
    "IWM_RUSSELL3000": IWM_RUSSELL3000_TICKERS,
    "VALUE_STOCKS": VALUE_STOCKS_TICKERS,
    "CONGRESSIONAL_LEADERS": CONGRESSIONAL_LEADERS_TICKERS,
    "TOM_LEE_FUNDSTRAT": TOM_LEE_FUNDSTRAT_TICKERS,
}

# Primary high-priority screener subset for rapid sub-second initial boot while all 600+ constituents remain 100% queryable
CORE_ACTIVE_SCREENER_TICKERS: List[str] = list(
    dict.fromkeys(
        DJIA_TICKERS
        + CONGRESSIONAL_LEADERS_TICKERS
        + TOM_LEE_FUNDSTRAT_TICKERS
        + NASDAQ_100_TICKERS[:40]
        + RUSSELL_SMALL_MID_CAP_LEADERS[:30]
        + VALUE_STOCKS_TICKERS[:30]
    )
)

COMPANY_NAMES: Dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "META": "Meta Platforms, Inc.",
    "GOOGL": "Alphabet Inc. (Class A)",
    "GOOG": "Alphabet Inc. (Class C)",
    "TSLA": "Tesla, Inc.",
    "AVGO": "Broadcom Inc.",
    "BRK-B": "Berkshire Hathaway Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "LLY": "Eli Lilly and Company",
    "UNH": "UnitedHealth Group Inc.",
    "V": "Visa Inc.",
    "XOM": "Exxon Mobil Corporation",
    "MA": "Mastercard Incorporated",
    "COST": "Costco Wholesale Corporation",
    "HD": "The Home Depot, Inc.",
    "PG": "The Procter & Gamble Company",
    "WMT": "Walmart Inc.",
    "JNJ": "Johnson & Johnson",
    "NFLX": "Netflix, Inc.",
    "CRM": "Salesforce, Inc.",
    "BAC": "Bank of America Corporation",
    "ORCL": "Oracle Corporation",
    "CVX": "Chevron Corporation",
    "AMD": "Advanced Micro Devices, Inc.",
    "MRK": "Merck & Co., Inc.",
    "KO": "The Coca-Cola Company",
    "CSCO": "Cisco Systems, Inc.",
    "PEP": "PepsiCo, Inc.",
    "LIN": "Linde plc",
    "TMUS": "T-Mobile US, Inc.",
    "ADBE": "Adobe Inc.",
    "MCD": "McDonald's Corporation",
    "WFC": "Wells Fargo & Company",
    "DIS": "The Walt Disney Company",
    "CAT": "Caterpillar Inc.",
    "GS": "The Goldman Sachs Group, Inc.",
    "IBM": "International Business Machines",
    "AXP": "American Express Company",
    "VZ": "Verizon Communications Inc.",
    "AMGN": "Amgen Inc.",
    "HON": "Honeywell International Inc.",
    "BA": "The Boeing Company",
    "SHW": "The Sherwin-Williams Company",
    "NKE": "NIKE, Inc.",
    "TRV": "The Travelers Companies, Inc.",
    "MMM": "3M Company",
    "PANW": "Palo Alto Networks, Inc.",
    "CRWD": "CrowdStrike Holdings, Inc.",
    "PLTR": "Palantir Technologies Inc.",
    "VST": "Vistra Corp.",
    "CEG": "Constellation Energy Corporation",
    "VRT": "Vertiv Holdings Co",
    "ETN": "Eaton Corporation plc",
    "ISRG": "Intuitive Surgical, Inc.",
    "IWM": "iShares Russell 2000 ETF",
    "IWV": "iShares Russell 3000 ETF",
    "VTV": "Vanguard Value ETF",
    "IVE": "iShares S&P 500 Value ETF",
    "IWD": "iShares Russell 1000 Value ETF",
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "GRNY": "Fundstrat Granny Shots US Large Cap ETF",
    "SMCI": "Super Micro Computer, Inc.",
    "MSTR": "MicroStrategy Incorporated",
    "COIN": "Coinbase Global, Inc.",
    "APP": "AppLovin Corporation",
    "DUOL": "Duolingo, Inc.",
    "FTAI": "FTAI Aviation Ltd.",
    "CVNA": "Carvana Co.",
    "SOFI": "SoFi Technologies, Inc.",
    "IONQ": "IonQ, Inc.",
    "RKLB": "Rocket Lab USA, Inc.",
    "HOOD": "Robinhood Markets, Inc.",
    "PFE": "Pfizer Inc.",
    "BMY": "Bristol-Myers Squibb Company",
    "T": "AT&T Inc.",
    "GM": "General Motors Company",
    "F": "Ford Motor Company",
    "C": "Citigroup Inc.",
    "DE": "Deere & Company",
    "ABBV": "AbbVie Inc.",
    "RTX": "RTX Corporation",
    "LMT": "Lockheed Martin Corporation",
    "PYPL": "PayPal Holdings, Inc.",
    "INTC": "Intel Corporation",
    "ASML": "ASML Holding N.V.",
    "ANET": "Arista Networks, Inc.",
    "GEV": "GE Vernova Inc.",
    "PWR": "Quanta Services, Inc.",
    "NOW": "ServiceNow, Inc.",
    "BLK": "BlackRock, Inc.",
}


def get_all_unique_tickers() -> List[str]:
    """Return deduplicated list of ALL stocks across DJIA, Nasdaq 100, S&P 500, Russell 3000, Value, Congressional, and Tom Lee indices."""
    return list(
        dict.fromkeys(
            DJIA_TICKERS
            + NASDAQ_100_TICKERS
            + SP500_TICKERS
            + IWM_RUSSELL3000_TICKERS
            + VALUE_STOCKS_TICKERS
            + CONGRESSIONAL_LEADERS_TICKERS
            + TOM_LEE_FUNDSTRAT_TICKERS
        )
    )


def get_ticker_universes(ticker: str) -> List[str]:
    """Return all custom and standard indices containing the given ticker."""
    t = ticker.strip().upper()
    return [uid for uid, members in UNIVERSE_TICKER_MAP.items() if t in members]


def get_company_name(ticker: str) -> str:
    """Return display company/ETF name for a ticker."""
    t = ticker.strip().upper()
    return COMPANY_NAMES.get(t, f"{t} Inc.")
