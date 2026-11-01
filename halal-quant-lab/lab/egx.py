"""Egyptian Exchange (EGX) universe on Yahoo Finance (".CA" suffix) with a halal business filter.

Yahoo carries most liquid EGX stocks; tickers it does not have are dropped automatically.
Business exclusions (conservative, by company activity): conventional banks, brokers / investment
banks / non-Islamic financial services, tobacco, hotels and resorts (alcohol). Islamic banks
(ADIB, Faisal, Al Baraka) are kept. Financial ratios are NOT checked here - verify with the
EGX33 Shariah Index constituents or a Shariah screener before trading.
"""
EGX_TICKERS = """
ABUK ACGC ADIB AFDI AIFI AJWA ALCN AMER AMES AMOC APSW ARCC ASCM ASPI ATQA AUTO BINV BIOC BONY
CAED CCAP CEFM CERA CICH CIRA CLHO COMI COPR COSG CPCI CSAG DAPH DEIN DOMT DSCW EALR EAST EBSC
ECAP EDBM EEII EFIC EFID EFIH EGAL EGCH EGREF EGSA EGTS EHDR EIUD EKHO ELEC ELKA ELNA ELSH EMFD
ENGC EPCO ESRS ETEL ETRS FAIT FAITA FERC FWRY GBCO GDWA GGCC GOCO GSSC HELI HRHO ICFC IDRE INFI
ISMA ISPH JUFO KABO KIMA KRDI KWIN KZPC LCSW LUTS MAAL MASR MBSC MCQE MCRO MENA MEPA MFPC MFSC
MHOT MICH MILS MIPH MNHD MOED MOIL MOSC MPCI MPRC MTIE NAHO NCCW NEDA NINH NIPH OBRI OCDI ODIN
OFH OIH OLFI ORAS ORHD ORWE PACH PHAR PHDC PHTV POUL PRCL PRDC RACC RAKT RAYA RMDA ROTO RREI
RTVC SAUD SCEM SCTS SDTI SEIG SIPC SKPC SMFR SMPP SNFC SPHT SPIN SPMD SUGR SVCE SWDY TALM TANM
TMGH TORA UASG UEFM UEGC UNIP UNIT WCDF WKOL ZEOT ZMID
""".split()

EXCLUDED = {
    # conventional banks
    "COMI": "conventional bank", "CIEB": "conventional bank", "QNBA": "conventional bank",
    "HDBK": "conventional bank", "EXPA": "conventional bank", "CANA": "conventional bank",
    "SAIB": "conventional bank", "UBEE": "conventional bank", "EGBE": "conventional bank",
    # brokers, investment banks, consumer/mortgage finance
    "HRHO": "investment bank / brokerage", "BTFH": "investment bank / brokerage",
    "CICH": "brokerage", "AIFI": "financial services", "EFIH": "financial services",
    "PRMH": "financial services", "CNFN": "consumer finance", "VALU": "consumer finance",
    # tobacco
    "EAST": "tobacco",
    # hotels and resorts (alcohol)
    "EGTS": "hotels / resorts", "MHOT": "hotels", "PHTV": "hotels", "SPHT": "hotels",
    "RTVC": "hotels / tourism",
}


def halal_egx():
    return [t for t in EGX_TICKERS if t not in EXCLUDED]
