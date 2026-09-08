"""Morning scan for Uriel's trading desk.
Step 1: TradingView screener (one request, whole US market): large caps in uptrend that closed green.
Step 2: yfinance daily bars only for those names, to count red days and find the pullback low.
Output: scan.json (schema read by the artifact page)."""
import json, sys, datetime as dt, warnings, urllib.request
warnings.filterwarnings('ignore')
import yfinance as yf, pandas as pd

req={"filter":[
  {"left":"market_cap_basic","operation":"greater","right":20_000_000_000},
  {"left":"close","operation":"greater","right":50},
  {"left":"close","operation":"greater","right":"SMA50"},
  {"left":"SMA50","operation":"greater","right":"SMA200"},
  {"left":"type","operation":"equal","right":"stock"},
  {"left":"exchange","operation":"in_range","right":["NASDAQ","NYSE"]}],
 "columns":["name","description","close","change","SMA20","SMA50","SMA200","High.1M","market_cap_basic","earnings_release_next_date"],
 "sort":{"sortBy":"market_cap_basic","sortOrder":"desc"},"range":[0,600]}
r=urllib.request.Request('https://scanner.tradingview.com/america/scan',data=json.dumps(req).encode(),headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'})
tv=json.load(urllib.request.urlopen(r,timeout=40))
trend={}
for row in tv['data']:
    n,desc,c,chg,s20,s50,s200,h1m,mc,ed=row['d']
    if c is None or s50 is None: continue
    trend[n]=dict(name=desc,last=round(c,2),ma50=round(s50,2),ma200=round(s200,2) if s200 else None,ma20=round(s20,2) if s20 else None,
        mcapB=round(mc/1e9) if mc else None,earnings=str(dt.datetime.fromtimestamp(ed,dt.UTC).date()) if ed else None,green_tv=bool(chg and chg>0))
if len(trend)<20: sys.exit('SCAN FAILED: TradingView returned only %d names'%len(trend))
print('TradingView: %d large caps in uptrend'%len(trend))

# bars for pullback structure (only names that closed green per TradingView, ~half)
cands=[s for s,v in trend.items() if v['green_tv']]
ysyms=[s.replace('.', '-') for s in cands]
end=dt.date.today()+dt.timedelta(days=1); start=end-dt.timedelta(days=60)
data=yf.download(ysyms,start=start,end=end,auto_adjust=True,progress=False,group_by='ticker',threads=True)
out=[]; lastdate=None; ok=0
for s,ys in zip(cands,ysyms):
    try:
        df=data[ys].dropna()
        if len(df)<25: continue
        ok+=1
        c=df['Close']; chg=c.diff(); green=bool(chg.iloc[-1]>0); last=float(c.iloc[-1])
        red=0;i=-2
        while i>=-10 and chg.iloc[i]<0: red+=1;i-=1
        hi20=float(c.iloc[-25:-1].max()); dd=(hi20-last)/hi20*100
        ma20=float(c.rolling(20).mean().iloc[-1]); dist20=(last-ma20)/ma20*100
        lastdate=max(lastdate or '',str(df.index[-1].date()))
        setup=None
        if green and 2<=red<=6: setup='strict'
        elif green and 3<=dd<=8 and abs(dist20)<=2.5: setup='late'
        elif green and red>=2 and dd<3: setup='shallow'
        if not setup: continue
        t=trend[s]
        out.append(dict(sym=s,name=t['name'],last=round(last,2),ma50=t['ma50'],ma200=t['ma200'],red=int(red),green=green,
            dist20=round(dist20,1),dd=round(dd,1),mcapB=t['mcapB'],earnings=t['earnings'],setup=setup))
    except Exception: pass
if ok<len(cands)*0.5: sys.exit('SCAN FAILED: bars downloaded for only %d/%d'%(ok,len(cands)))
order={'strict':0,'late':1,'shallow':2}; out.sort(key=lambda x:(order[x['setup']],-(x['mcapB'] or 0)))
doc=dict(date=lastdate,scannedAt=str(dt.date.today()),universe=len(trend),inTrend=len(trend),
    note='מקור: סקרינר TradingView (כל המניות מעל $20B בנאסד"ק ו-NYSE) + נרות יומיים. כולל תאריך דוח הבא.',rows=out)
json.dump(doc,open('scan.json','w'),ensure_ascii=False,indent=1)
print('OK',lastdate,len(trend),len(out),[o['sym']+':'+o['setup'] for o in out])
