"""Capture the real app using generated household data and public market prices.

Run with the finance app's Python environment and --source PATH. No source data,
secrets, reports or caches are copied. All app writes stay in .cache/fincopilot.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.cache' / 'fincopilot'
OUTPUT = WORK / 'captures'
PORT = 8063


def prepare(source):
    if (WORK / 'data').exists():
        raise RuntimeError('Use a fresh .cache/fincopilot directory for each capture run.')
    for name in ('src', 'assets'):
        shutil.copytree(source / name, WORK / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(source / 'app.py', WORK / 'app.py')
    configure_household()


def configure_household():
    config = WORK / 'src' / 'config'
    (config / 'income.py').write_text("SALARY = {'demo': {'month': '2020-01', 'amount': 26000}}\nEXTRA = {}\n")
    (config / 'expenses.py').write_text(
        "FIXED_BILLS = {'rent': 8900, 'subscriptions': 300, 'transport': 850, 'energy': 900}\n"
        "VARIABLE_BILLS = {'grocerie': 3600, 'restaurant': 900, 'health': 350, 'personal': 4200}\n"
        "DISTRIBUTED_BILLS = {'annual_cover': {'months': [11], 'amount': 650}}\n")
    (config / 'investing.py').write_text(
        "INVEST = {'demo': {'month': '2020-01', 'amount': 2400}}\n"
        "INVEST_CHILD = {'demo': {'month': '2020-01', 'amount': 400}}\n"
        "TICKERS_ENTRY = [{'ticker': 'IWDA.AS', 'fixed_drawdown': .1, 'ma_window': 200}, {'ticker': 'HEAL.AS', 'fixed_drawdown': .15, 'ma_window': 200}]\n"
        "EXIT_STOP_LOSS_PCT = -.1\nEXIT_TAKE_PROFIT_PCT = .15\n")
    (config / 'portfolio.py').write_text(
        "CORE_TICKERS = ['IWDA.AS']\nISIN_MAP = {}\n"
        "PORTFOLIO_CONTEXT = {'IWDA.AS': 'iShares Core MSCI World UCITS ETF', 'HEAL.AS': 'Healthcare Innovation ETF'}\n"
        "TARGET_WEIGHTS = {'IWDA.AS': .90}\nTACTICAL_WEIGHT = .10\n"
        "INVEST_SHARE_01 = 1\nINVEST_SHARE_02 = 0\nHOLDINGS_NOTIFY_TIME = '17:30'\n"
        "SKAT_RATE = .15\nOPPORTUNITY_SHARE = .25\nREBALANCE_TOLERANCE = .03\n")
    system = "from pathlib import Path\nDEBUG = True\nBACKUP_ENABLED = False\nBACKUP_ROOT = Path('disabled')\n"
    system += "BANK_ACCOUNT_TYPE = 'l&s'\nTHRESHOLD = .75\nAKASSE = 0\nHOME_VALUE_TARGET = 800000\nNR_MONTHS_BUFFER = 4\nRECOMMENDED_BALANCE_ROUNDING = 1000\nUSE_DUMMY = False\nINTERNAL_FLOWS_CATS = ['nordnet', 'debt', 'child', 'downpayment']\n"
    for key, path in {
        'SAVINGS_FILE': 'concat/txn/Savings.csv', 'TRANS_MAIN': 'concat/txn/Main.csv',
        'TRANS_SUB': 'concat/txn/Sub.csv', 'TRANS_MAIN_UPDATE': 'updates/Main_update.csv',
        'TRANS_SUB_UPDATE': 'updates/Sub_update.csv', 'POSITIONS': 'concat/ledger/Positions.csv',
        'POSITIONS_UPDATE': 'updates/Positions_update.csv', 'CASHFLOWS': 'concat/ledger/Cashflows.csv',
        'PORTFOLIO_HISTORY_FILE': 'portfolio/portfolio_history.csv', 'HYPE_CACHE_FILE': 'portfolio/hype_prices.csv',
    }.items():
        system += f"{key} = Path('data/{path}')\n"
    (config / 'system.py').write_text(system)
    # Replace the app's personal greeting and default watch ticker before import.
    for name in ('src/app/callbacks/__init__.py', 'src/app/layouts/tactical.py'):
        p = WORK / name
        text = p.read_text(encoding='utf-8').replace("greet + ', Abdul'", "'Synthetic household'").replace('VWCE.DE', 'IWDA.AS')
        p.write_text(text, encoding='utf-8')
    # Rename the displayed tab while preserving the app's internal callback IDs.
    for name in ('src/app/layout.py', 'src/app/layouts/decision.py'):
        p = WORK / name
        p.write_text(p.read_text(encoding='utf-8').replace('"Decision"', '"Plan"').replace("'Decision'", "'Plan'"), encoding='utf-8')


def household_fixtures(prices, asof):
    """A reconciled fictional ledger; synthetic lots execute at public daily closes."""
    import random
    import pandas as pd
    rng = random.Random(73)
    current = asof.to_period('M')
    review = current - 1
    rows, lots, deposits = [], [], []

    def payment(date, label, amount):
        if date <= asof:
            rows.append({'date': date, 'category': 'Demo ' + label, 'amount': round(amount, 2)})

    for month in pd.period_range(current - 12, current, freq='M'):
        payment(month.start_time - pd.offsets.BDay(1), 'salary', 26000)
        expenses = [('rent', 8900, 1), ('subscriptions', 300, 3), ('transport', 850, 5),
                    ('energy', 900, 8), ('health', 350, 10), ('personal', 4200, 12)]
        for label, base, day in expenses:
            payment(month.start_time + pd.Timedelta(days=day - 1), label, -base * rng.uniform(.96, 1.04))
        for day in [4, 11, 18, 25]:
            payment(month.start_time + pd.Timedelta(days=day - 1), 'groceries', -900 * rng.uniform(.93, 1.07))
        # A deliberate frequency increase in the completed review cycle.
        dining_days = [6, 9, 13, 17, 21, 23] if month == review else [13, 23]
        for day in dining_days:
            payment(month.start_time + pd.Timedelta(days=day - 1), 'restaurant', -300)
        payment(month.start_time + pd.Timedelta(days=19), 'child', -400)
        payment(month.start_time + pd.Timedelta(days=20), 'downpayment', -1000)
        buy_day = month.start_time + pd.Timedelta(days=14)
        dates = prices['IWDA.AS'].dropna().index
        dates = dates[(dates >= buy_day) & (dates <= asof)]
        if dates.empty or dates[0].to_period('M') != month:
            continue
        buy_day = dates[0]
        payment(buy_day, 'invest', -2200)
        deposits.append({'id': f'DEMO-{month}', 'date': str(buy_day.date()), 'amount_dkk': 2200, 'type': 'deposit'})
        for ticker, strategy, budget in [('IWDA.AS', 'core', 1900), ('HEAL.AS', 'tactical', 300)]:
            close = prices[ticker].dropna().loc[:buy_day]
            trade_day, price = close.index[-1], float(close.iloc[-1])
            fx = float(prices['EURDKK=X'].dropna().loc[:trade_day].iloc[-1])
            lots.append(dict(trade_id=f'DEMO-{month}-{ticker}', ticker=ticker, currency='EUR', strategy=strategy,
                             shares=budget / (price * fx), entry_date=str(trade_day.date()), entry_price=price,
                             entry_value_dkk=budget, status='open', stop_loss=None, take_profit=None, max_days=None,
                             close_trade_id=None, close_date=None, close_price=None, close_value_dkk=None))
    bank = pd.DataFrame(rows).sort_values('date', kind='stable').reset_index(drop=True)
    bank['balance'] = 24000 + bank['amount'].cumsum()
    assert (bank['balance'].diff().iloc[1:] - bank['amount'].iloc[1:]).abs().max() < 1e-8
    for col in ['amount', 'balance']:
        bank[col] = bank[col].map(lambda x: f'{x:.2f}'.replace('.', ','))
    bank['date'] = bank['date'].dt.strftime('%Y-%m-%d')
    bank['currency'] = 'DKK'
    positions = pd.DataFrame(lots)
    sub = bank.loc[bank['category'] == 'Demo salary'].copy()
    sub['category'] = 'Demo unused secondary account'
    sub['amount'] = '0,00'
    sub['balance'] = '0,00'
    history = []
    for day in prices['IWDA.AS'].dropna().index:
        active = positions[pd.to_datetime(positions['entry_date']) <= day]
        if active.empty or day > asof:
            continue
        fx = float(prices['EURDKK=X'].dropna().loc[:day].iloc[-1])
        value = sum(float(row.shares) * float(prices[row.ticker].dropna().loc[:day].iloc[-1]) * fx
                    for row in active.itertuples())
        cost = float(active['entry_value_dkk'].sum())
        history.append({'date': str(day.date()), 'capital': value, 'weighted_return': value / cost - 1,
                        'unrealized_pl': value - cost, 'iwda_price': float(prices.loc[day, 'IWDA.AS'])})
    return {
        'concat/txn/Main.csv': bank,
        'concat/txn/Sub.csv': sub,
        'concat/txn/Savings.csv': pd.DataFrame(columns=['month', 'notes']),
        'concat/ledger/Positions.csv': positions,
        'concat/ledger/Cashflows.csv': pd.DataFrame(deposits),
        'portfolio/portfolio_history.csv': pd.DataFrame(history),
    }


def serve():
    os.chdir(WORK)
    sys.path.insert(0, str(WORK))
    sys.argv.append('--debug')
    configure_household()
    import pandas as pd
    import src.behaviour.sync as sync
    sync.sync_downloads_to_updates = lambda: None
    import src.backup as backup
    backup.run_backup_check = lambda *a, **k: None
    import yfinance as yf
    symbols = ['IWDA.AS', '^VIX', 'CL=F', 'GC=F', '^GSPC', '^TNX', 'DKK=X', 'EURDKK=X', 'USDDKK=X',
               'HEAL.AS', 'IS0E.DE', 'RBOE.AS', 'IQQ0.DE', 'EUNL.DE']
    cache = WORK / 'public-markets.csv'
    if cache.exists():
        prices = pd.read_csv(cache, index_col=0, parse_dates=True)
    else:
        prices = pd.DataFrame()
    missing = [symbol for symbol in symbols if symbol not in prices or prices[symbol].dropna().empty]
    if missing:
        fetched = yf.download(missing, period='2y', auto_adjust=False, progress=False, timeout=25)['Close']
        prices = pd.concat([prices.drop(columns=missing, errors='ignore'), fetched], axis=1)
        for symbol in symbols[:9] + ['HEAL.AS']:
            if symbol not in prices or prices[symbol].dropna().empty:
                raise RuntimeError(f'Missing genuine public market data: {symbol}')
        prices.to_csv(cache)
    asof = pd.Timestamp.now().normalize()
    fixtures = household_fixtures(prices, asof)
    for relative, frame in fixtures.items():
        target = WORK / 'data' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(target, index=False)
    # Generic fixture labels map to the app's categories without using private transfer descriptions.
    import src.behaviour.transactions.categorizer as categorizer
    expense_labels = {'rent': 'rent', 'subscriptions': 'subscriptions', 'transport': 'transport',
                      'energy': 'energy', 'health': 'health', 'personal': 'personal', 'grocerie': 'groceries',
                      'restaurant': 'restaurant', 'nordnet': 'invest', 'child': 'child', 'downpayment': 'downpayment'}
    categorizer.CATEGORIES_MAIN = {'income': {'salary': [r'^demo salary']},
                                  'expense': {key: ['^demo ' + label] for key, label in expense_labels.items()}}
    categorizer.CATEGORIES_SUB = categorizer.CATEGORIES_MAIN
    # Every market view reads the same genuine public snapshot, never synthetic prices.
    def download(tickers, **kwargs):
        requested = tickers.split() if isinstance(tickers, str) else list(tickers)
        selected = prices.reindex(columns=requested)
        if kwargs.get('start'):
            selected = selected.loc[pd.Timestamp(kwargs['start']).tz_localize(None):]
        if kwargs.get('end'):
            selected = selected.loc[:pd.Timestamp(kwargs['end']).tz_localize(None)]
        return pd.concat({'Close': selected}, axis=1)
    yf.download = download
    import src.portfolio.position as position
    def info(ticker):
        values = prices[ticker].dropna()
        return dict(price=float(values.iloc[-1]), previous_close=float(values.iloc[-2]),
                    ma50=float(values.tail(50).mean()), ma200=float(values.tail(200).mean()),
                    year_high=float(values.tail(252).max()), currency='EUR' if ticker.endswith(('.DE', '.AS')) else 'USD')
    position.get_ticker_info = info
    position.get_fx_rate = lambda currency, *a: 1.0 if currency == 'DKK' else float(prices[f'{currency}DKK=X'].dropna().iloc[-1])
    position.save_portfolio_snapshot = lambda *a, **k: None
    import src.portfolio.hype as hype
    hype._save_prices({c: prices[c].dropna() for c in prices})
    import src.app.callbacks.fincopilot as fc
    # Example text is written for these fixtures. No private reports or AI keys are read.
    fc._load_report = lambda: 'Synthetic household example. Scripted for this walkthrough.\n\n*Generated with: Scripted example*'
    fc._get_or_make_briefing = lambda *a: {
        'matters': 'Synthetic example: check the scheduled annual expense before allocating the remaining surplus.',
        'working': 'The fictional household has regular income and a separate monthly investment allocation.',
        'i_would_do': 'Review the configured cash-buffer target alongside the planned purchases. These messages are scripted, not an AI assessment.',
    }
    fc.ensure_todays_report = lambda **k: True
    fc.generate_news_snapshot = lambda: None
    fc.read_news_snapshot = lambda: None
    fc._call_llm = lambda question, **kwargs: (
        'Synthetic example · scripted\n\nThe figures are calculated by the application. Review the fictional household’s scheduled expense, cash-buffer target and allocations before interpreting the plan. This scripted response demonstrates the chat interface; it is not evidence of AI answer quality.',
        'Scripted example')
    from app import app, state
    review_month = str(asof.to_period('M') - 1)
    review_row = state['MONTHLY_SUMMARY'].loc[
        state['MONTHLY_SUMMARY']['month'].astype(str) == review_month].iloc[0]
    assert float(review_row['income']) == 26000, 'The review cycle must contain exactly one salary'
    assert abs(float(review_row['nwc']) - float(review_row['income'] + review_row['expense'])) < 2, 'Generated savings must reconcile with net income'
    assert 0 < float(review_row['nwc']) < 9000, 'Review savings are outside the fictional household budget'
    from src.app.callbacks.review import _month_habits
    assert _month_habits(state, review_month), 'The synthetic review needs a genuine computed habit finding'
    from src.app.callbacks.common import _build_ticker_fig
    iwda_lots = fixtures['concat/ledger/Positions.csv'].query("ticker == 'IWDA.AS'")
    chart = _build_ticker_fig('IWDA.AS', buy_lots=iwda_lots)
    line = next(trace for trace in chart.data if trace.name == 'IWDA.AS')
    markers = next(trace for trace in chart.data if trace.name == 'Your buys')
    closes = {pd.Timestamp(day).date(): float(value) for day, value in zip(line.x, line.y)}
    assert all(abs(closes[pd.Timestamp(day).date()] - value) < 1e-8
               for day, value in zip(markers.x, markers.y)), 'Trade markers must lie on the market-price line'
    assert position.get_monthly_return_trend(6), 'The portfolio sparkline needs actual synthetic-position history'
    receipt = {'household': 'reconciled generated ledger, seed 73; no private data copied', 'review_month': review_month,
               'plan_month': str(asof.to_period('M')), 'allocation_tab': 'Plan',
               'holdings': {'core': 'IWDA.AS', 'tactical': 'HEAL.AS'},
               'trades': 'fictional dates and allocations, executed at the matching public closing price',
               'review_checks': {'salary': float(review_row['income']), 'expense': float(review_row['expense']), 'generated': float(review_row['nwc'])},
               'markets': {c: str(prices[c].dropna().index[-1].date()) for c in prices if not prices[c].dropna().empty},
               'briefing_and_chat': 'scripted; no AI provider called'}
    (WORK / 'provenance.json').write_text(json.dumps(receipt, indent=2))
    app.run_server(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)


def capture(tabs=None):
    from playwright.sync_api import sync_playwright
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (WORK / 'server.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, __file__, '--serve'], cwd=WORK, stdout=log, stderr=log)
        try:
            for _ in range(180):
                if process.poll() is not None:
                    raise RuntimeError((WORK / 'server.log').read_text(encoding='utf-8'))
                try:
                    with urlopen(f'http://127.0.0.1:{PORT}', timeout=1):
                        break
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError('Capture app did not start; inspect server.log')
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='chrome', headless=True)
                page = browser.new_page(viewport={'width': 430, 'height': 932}, device_scale_factor=2,
                                        is_mobile=True, has_touch=True, color_scheme='dark', reduced_motion='reduce')
                page.add_init_script("localStorage.setItem('fincopilot-theme','dark');sessionStorage.setItem('pwaBarDismissed','1')")
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{PORT}', wait_until='networkidle')
                page.add_style_tag(content='''
                    #bank-sync-btn { color: var(--fc-text) !important; }
                    .dash-debug-menu, .fc-chat-keyboard-hint, .fc-chat-composer-meta { display:none !important; }
                    .fc-chat-suggestions { display:grid !important; grid-template-columns:1fr 1fr; overflow:visible !important; }
                    .fc-chat-messages { min-height:360px !important; }
                    body { min-height:0 !important; }
                ''')
                for tab in tabs or ('Overview', 'Review', 'Forecast', 'Invest', 'Tactical', 'Plan', 'FinCopilot'):
                    page.locator('#tabs-dropdown .Select-control').click()
                    page.locator('#tabs-dropdown .Select-menu-outer').get_by_text(tab, exact=True).click()
                    page.wait_for_timeout(2500)
                    if tab == 'Review':
                        receipt = json.loads((WORK / 'provenance.json').read_text())
                        page.locator('#month-input').fill(receipt['review_month'])
                        page.locator('#month-input').press('Tab')
                        page.wait_for_timeout(1500)
                        assert 'More often' in page.locator('#habits-list').inner_text(), 'Review habit frequency change is missing'
                    if tab == 'Invest':
                        assert 'IWDA.AS' in page.locator('#invest-signals').inner_text()
                        assert 'HEAL.AS' in page.locator('#invest-signals').inner_text()
                    # Keep the genuine app UI and footer, omit unused collapsed sections.
                    page.evaluate('''() => {
                        const unused=['order trend','savings trend','savings table','read full analysis','read news summary'];
                        document.querySelectorAll('details:not([open])').forEach(e=>{
                            const label=e.querySelector(':scope > summary')?.innerText.trim().toLowerCase() || '';
                            if(unused.some(name=>label.startsWith(name))) e.style.display='none';
                        });
                        const heading=[...document.querySelectorAll('*')].find(e=>e.children.length===0 && e.textContent.trim().toLowerCase()==='investment details');
                        if(heading) heading.parentElement.parentElement.style.display='none';
                    }''')
                    if tab == 'Review':
                        assert 'More often' in page.locator('#habits-list').inner_text(), 'Capture styling hid the habit finding'
                    if tab == 'Tactical':
                        page.locator('.app-footer').screenshot(path=str(OUTPUT / 'tactical-footer.png'))
                        page.evaluate('document.activeElement.blur();window.scrollTo(0,0)')
                        chart = page.locator('#ticker-chart').bounding_box()
                        pick = page.locator('.tactical-control-row').bounding_box()
                        assert chart and pick
                        page.screenshot(path=str(OUTPUT / 'tactical.png'), full_page=True, clip={'x':0,'y':0,'width':430,'height':pick['y']-12})
                        detail_top = max(0, pick['y'] - 24)
                        page.screenshot(path=str(OUTPUT / 'tactical-detail.png'), full_page=True, clip={'x':0,'y':detail_top,'width':430,'height':chart['y']+chart['height']-detail_top+20})
                    else:
                        if tab == 'FinCopilot':
                            page.evaluate('document.activeElement.blur();window.scrollTo(0,0)')
                            page.screenshot(path=str(OUTPUT / 'briefing.png'), full_page=True)
                            page.locator('#fc-view-ask').click()
                            page.locator('#fincopilot-question').fill('What should I keep in mind this month?')
                            page.locator('#fincopilot-btn').click()
                            page.get_by_text('Synthetic example · scripted', exact=False).wait_for()
                            page.wait_for_timeout(500)
                        page.evaluate('document.activeElement.blur();window.scrollTo(0,0)')
                        footer = page.locator('.app-footer').bounding_box()
                        height = footer['y'] + footer['height'] + 16 if tab != 'FinCopilot' else page.evaluate('document.documentElement.scrollHeight')
                        page.screenshot(path=str(OUTPUT / f'{tab.lower()}.png'), full_page=True,
                                        clip={'x':0, 'y':0, 'width':430, 'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), tab
                    print(f'Captured {tab}', flush=True)
                assert not errors, errors
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--tab', action='append', choices=('Overview', 'Review', 'Forecast', 'Invest', 'Tactical', 'Plan', 'FinCopilot'), help='Recapture selected tabs only; repeat to select more than one.')
    args = parser.parse_args()
    if args.serve:
        serve()
    else:
        if args.source:
            prepare(args.source.resolve())
        capture(args.tab)
