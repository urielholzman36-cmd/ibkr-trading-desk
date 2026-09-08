"""Morning scan for Uriel's trading desk. Output: scan.json (schema read by the artifact page)."""
import yfinance as yf, pandas as pd, datetime as dt, json, warnings, sys
warnings.filterwarnings('ignore')
U="""AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA BRK-B LLY JPM V MA UNH XOM COST HD PG JNJ ABBV WMT NFLX BAC CRM ORCL KO CVX MRK AMD PEP TMO CSCO ADBE ACN MCD LIN ABT WFC GE IBM CAT TXN INTU QCOM ISRG AMGN NOW GS AMAT BKNG DIS PM SPGI AXP MS T VZ RTX HON LOW BLK UBER NEE PFE ETN SYK UNP PGR BSX ADP LMT COP SCHW C PANW GILD ANET VRTX ADI KLAC LRCX MU PLTR CRWD DE MDT BA CB ELV REGN SBUX PLD TMUS CMCSA CI SO ZTS DUK ICE MO KKR APH SHW WM CTAS TT MCK PH GLW ITW EMR MRVL AON FDX GD NKE ORLY CME CVS PNC USB TGT MAR ECL MSI ROP TDG ABNB DASH APP MELI ASML TSM SHOP SNPS CDNS FTNT DDOG ZS WDAY TEAM ARM COIN HOOD AXON CEG VST GEV NRG LNG WMB OKE EOG SLB PSX VLO MPC BKR HAL DELL HPE HPQ SMCI STX WDC NXPI ON MCHP JCI CARR OTIS URI PWR FAST ODFL CPRT ROST DHI LEN NVR PHM VRSK IT CTSH INFY SAP NVO AZN UL RIO BHP TTE SHEL BP ENB CNQ SU TD RY BN MUFG SONY TM""".split()
end=dt.date.today()+dt.timedelta(days=1); start=end-dt.timedelta(days=400)
data=yf.download(U,start=start,end=end,auto_adjust=True,progress=False,group_by='ticker',threads=True)
rows=[]
for s in U:
    try:
        df=data[s].dropna()
        if len(df)<210: continue
        c=df['Close']; ma50=c.rolling(50).mean(); ma200=c.rolling(200).mean(); ma20=c.rolling(20).mean()
        last=float(c.iloc[-1]); chg=c.diff(); green=bool(chg.iloc[-1]>0)
        red=0; i=-2
        while i>=-10 and chg.iloc[i]<0: red+=1; i-=1
        hi20=float(c.iloc[-25:-1].max()); dd=(hi20-last)/hi20
        rows.append(dict(sym=s,last=round(last,2),ma50=round(float(ma50.iloc[-1]),2),ma200=round(float(ma200.iloc[-1]),2),
            above50=bool(last>ma50.iloc[-1]), ma50gt200=bool(ma50.iloc[-1]>ma200.iloc[-1]), red=red, green=green,
            dist20=round(float((last-ma20.iloc[-1])/ma20.iloc[-1]*100),1), dd=round(dd*100,1), lastdate=str(df.index[-1].date())))
    except Exception: pass
df=pd.DataFrame(rows)
if len(df)<100: sys.exit('SCAN FAILED: only %d tickers downloaded'%len(df))
trend=df[(df.above50)&(df.ma50gt200)&(df['last']>50)].copy()
def setup(r):
    if r.green and 2<=r.red<=6: return 'strict'
    if r.green and 3<=r.dd<=8 and abs(r.dist20)<=2.5: return 'late'
    if r.green and r.red>=2 and r.dd<3: return 'shallow'
    return None
trend['setup']=trend.apply(setup,axis=1)
cand=trend[trend.setup.notna()].sort_values(['setup','sym'])
out=[]
for r in cand.itertuples():
    mcap=None; earn=None; name=None
    try:
        t=yf.Ticker(r.sym); info=t.info or {}; name=info.get('shortName'); mc=info.get('marketCap')
        mcap=round(mc/1e9) if mc else None
        cal=t.calendar; ed=cal.get('Earnings Date') if isinstance(cal,dict) else None
        if ed: earn=str(ed[0]) if isinstance(ed,list) else str(ed)
    except Exception: pass
    out.append(dict(sym=r.sym,name=name,last=r.last,ma50=r.ma50,ma200=r.ma200,red=int(r.red),green=bool(r.green),dist20=r.dist20,dd=r.dd,mcapB=mcap,earnings=earn,setup=r.setup))
lastdate=str(df.lastdate.max())
doc=dict(date=lastdate,scannedAt=str(dt.date.today()),universe=int(len(df)),inTrend=int(len(trend)),note='',rows=out)
json.dump(doc,open('scan.json','w'),ensure_ascii=False,indent=1)
print('OK',lastdate,len(df),len(trend),len(out),[o['sym'] for o in out])
