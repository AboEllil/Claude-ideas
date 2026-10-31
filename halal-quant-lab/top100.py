"""Top 100 Shariah-compliant US companies, ranked by quality.

    python top100.py            # uses cached fundamentals/prices in data/
    python top100.py --refresh  # re-download

Steps
  1. ~400 large US companies (S&P 500 non-financials + large Nasdaq names).
  2. Shariah screen from lab/universe.py (business activity + debt/cash ratios).
  3. Keep market cap >= $10B (established, liquid).
  4. Quality score = average percentile rank of:
       profitability 40%  (return on equity, profit margin - each 20%)
       growth        20%  (revenue growth)
       strength      20%  (low debt / market cap)
       track record  20%  (5-year Sharpe ratio of the stock)
Writes reports/top100_halal.csv and reports/TOP100.md.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from lab.universe import DATA, fetch_fundamentals, screen

OUT = Path(__file__).resolve().parent / "reports"

BROAD = """
AAPL MSFT NVDA AVGO ORCL CRM ADBE AMD CSCO ACN IBM INTU NOW TXN QCOM AMAT LRCX KLAC ADI MU INTC PANW ANET
SNPS CDNS CRWD FTNT MSI APH TEL ROP ADSK WDAY MCHP NXPI ON MPWR KEYS GLW IT CDW HPQ HPE DELL NTAP STX WDC
SMCI TER ZBRA TYL PTC FICO AKAM FFIV SWKS QRVO ENPH FSLR GEN EPAM GDDY TRMB JBL FLEX PLTR DDOG ZS SNOW
TEAM MDB NET HUBS TTD APP MRVL ADP PAYX VRSN CTSH
GOOGL META NFLX DIS CMCSA T VZ TMUS CHTR EA TTWO OMC
AMZN TSLA HD LOW MCD SBUX NKE TJX ROST BKNG ABNB CMG ORLY AZO LULU DECK MAR HLT GM F YUM DRI TSCO ULTA BBY
EBAY POOL GRMN DPZ LVS WYNN MGM RL TPR NVR PHM LEN DHI GPC LKQ KMX APTV RCL CCL EXPE DASH UBER WSM BURL DKS
WMT COST PG KO PEP PM MO MDLZ CL KMB GIS KHC HSY STZ KDP MNST CHD CLX SYY KR TGT DG DLTR EL ADM BG TSN HRL
CAG CPB SJM MKC KVUE CASY BJ CELH
LLY UNH JNJ ABBV MRK TMO ABT DHR PFE AMGN ISRG SYK BSX MDT VRTX REGN GILD BMY ZTS CVS CI ELV HCA MCK COR
CAH IDXX DXCM IQV A WST RMD ALGN EW MTD TECH WAT ILMN HOLX BDX BAX STE COO PODD MRNA BIIB INCY VTRS ZBH
GEHC HUM CNC MOH LH DGX CRL DVA UHS RVTY SOLV
GE CAT RTX HON UNP UPS BA LMT DE ETN ITW PH EMR NOC GD TDG CSX NSC FDX WM RSG CTAS PCAR CMI ROK AME ODFL
FAST GWW URI CPRT VRSK OTIS CARR TT JCI LHX HWM IR XYL DOV SWK SNA PNR MAS EXPD CHRW JBHT LUV DAL UAL WAB
HII TXT BLDR GNRC AXON PWR VLTO FTV J LDOS BAH ROL ALLE AOS NDSN IEX HUBB EME FIX WSO LII GEV
XOM CVX COP EOG SLB OXY PSX MPC VLO WMB KMI OKE DVN FANG HAL BKR CTRA EQT APA TRGP
LIN SHW APD ECL NUE FCX NEM DD DOW PPG CTVA MLM VMC IFF ALB CF MOS STLD PKG IP AVY BALL AMCR CE LYB EMN RS
JPM BAC V MA O PLD MSTR
""".split()


def five_year_sharpe(tickers):
    px = yf.download(tickers, period="5y", auto_adjust=True, progress=False)["Close"]
    r = px.pct_change(fill_method=None)
    sh = r.mean() / r.std() * np.sqrt(252)
    tot = px.ffill().iloc[-1] / px.bfill().iloc[0] - 1
    return sh, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    tickers = list(dict.fromkeys(BROAD))
    print(f"screening {len(tickers)} companies ...")
    df = screen(tickers, refresh=a.refresh).set_index("ticker")
    f = pd.DataFrame(fetch_fundamentals(tickers)).T.reindex(df.index)
    df = df.join(f[["marketCap", "returnOnEquity", "profitMargins", "grossMargins", "revenueGrowth",
                    "earningsGrowth", "forwardPE"]].apply(pd.to_numeric, errors="coerce"))
    df.reset_index().to_csv(OUT / "broad_screen.csv", index=False)
    ok = df[df.compliant & (df.marketCap >= 10e9)].copy()
    print(f"{df.compliant.sum()} pass the Shariah screen, {len(ok)} with market cap >= $10B")

    sh, tot = five_year_sharpe(list(ok.index))
    ok["sharpe_5y"] = sh.reindex(ok.index)
    ok["return_5y"] = tot.reindex(ok.index)

    def rk(s, asc=True):
        return s.rank(pct=True, ascending=asc).fillna(0.5)

    ok["score"] = (0.2 * rk(ok.returnOnEquity.clip(-1, 1)) + 0.2 * rk(ok.profitMargins)
                   + 0.2 * rk(ok.revenueGrowth) + 0.2 * rk(ok.debt_to_mcap, asc=False)
                   + 0.2 * rk(ok.sharpe_5y))
    top = ok.sort_values("score", ascending=False).head(100)
    top.insert(0, "rank", range(1, len(top) + 1))
    cols = ["rank", "name", "sector", "industry", "marketCap", "score", "returnOnEquity", "profitMargins",
            "revenueGrowth", "debt_to_mcap", "cash_to_mcap", "sharpe_5y", "return_5y", "forwardPE"]
    top[cols].to_csv(OUT / "top100_halal.csv")

    def p(x):
        return "" if pd.isna(x) else f"{x:.0%}"

    lines = [
        "# Top 100 Shariah-compliant US companies (by quality score)",
        "",
        f"Generated {pd.Timestamp.now():%Y-%m-%d} from {len(tickers)} large US companies; "
        f"{int(df.compliant.sum())} pass the screen, {len(ok)} of those are $10B+.",
        "",
        "**Screen** (AAOIFI-style): no conventional finance/insurance, alcohol, tobacco, gambling, pork, "
        "entertainment, hotels, weapons makers or real estate; debt < 30% and cash < 30% of market cap.",
        "**Score**: average percentile of ROE, profit margin, revenue growth, low debt and 5-year Sharpe ratio "
        "(each 20%).",
        "",
        "> Research list, not a fatwa or investment advice. Ratios change every quarter - verify each name "
        "with a Shariah screener (Zoya, Musaffa, Islamicly) before buying, and purify any non-permissible "
        "income from dividends.",
        "",
        "| # | Ticker | Company | Sector | Mkt cap | Score | ROE | Margin | Rev growth | Debt/MC | 5y return |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t, r in top.iterrows():
        lines.append(f"| {r['rank']} | {t} | {r['name']} | {r.sector} | ${r.marketCap / 1e9:,.0f}B | "
                     f"{r.score:.2f} | {p(r.returnOnEquity)} | {p(r.profitMargins)} | {p(r.revenueGrowth)} | "
                     f"{p(r.debt_to_mcap)} | {p(r.return_5y)} |")
    rej = df[~df.compliant].reason.str.replace(r" \d+%", "", regex=True).str.replace("industry: ", "").value_counts()
    lines += ["", "## Why companies were rejected", "| Reason | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rej.items()]
    lines += ["", "## Sector mix of the top 100", "| Sector | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in top.sector.value_counts().items()]
    (OUT / "TOP100.md").write_text("\n".join(lines) + "\n")
    print(top[["name", "sector", "score"]].head(20).to_string())


if __name__ == "__main__":
    main()
