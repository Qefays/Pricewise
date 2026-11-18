"""Small, cached analytical views. Source observations remain immutable."""
import pandas as pd
import streamlit as st

@st.cache_data(max_entries=12, show_spinner=False)
def product_history(_data, signature, code):
    return _data.loc[_data.item_code.eq(code)].copy()

@st.cache_data(max_entries=24, show_spinner=False)
def coverage_views(_data, signature, state, district):
    data = area(_data, state, district)
    dates = pd.date_range(_data.date.min(), _data.date.max())
    daily = data.groupby('date', observed=True).size().reindex(dates, fill_value=0).rename('observations').rename_axis('date').reset_index()
    daily['month'] = daily.date.dt.strftime('%b %Y')
    daily['day'] = daily.date.dt.day
    groups = data.groupby('item_group', observed=True).agg(observations=('price','size'), products=('item_code','nunique')).reset_index()
    stats = dict(observations=len(data), products=data.item_code.nunique(), premises=data.premise_code.nunique(), days=data.date.nunique(), start=_data.date.min(), end=_data.date.max())
    return stats, daily, groups

def area(data, state, district):
    if state != 'All Malaysia':
        data = data[data.state.eq(state)]
    if district != 'All districts':
        data = data[data.district.eq(district)]
    return data

def period_summary(data, frequency='Daily'):
    rule = {'Daily':'D','Weekly':'W-SUN','Monthly':'ME'}[frequency]
    return data.set_index('date').resample(rule).agg(
        median=('price','median'), lower=('price',lambda s:s.quantile(.25)),
        upper=('price',lambda s:s.quantile(.75)), observations=('price','size'),
        premises=('premise_code','nunique')).reset_index()

def geographic_prices(data, by='state'):
    return data.groupby(by, observed=True).agg(median=('price','median'), lower=('price',lambda s:s.quantile(.25)), upper=('price',lambda s:s.quantile(.75)), premises=('premise_code','nunique')).reset_index()

def matched_change(data, start, end):
    left=data[data.date.eq(pd.Timestamp(start))][['premise_code','price']]
    right=data[data.date.eq(pd.Timestamp(end))][['premise_code','price']]
    joined=left.merge(right,on='premise_code',suffixes=('_start','_end'))
    joined['change_pct']=(joined.price_end/joined.price_start-1)*100
    return joined

def comparison_export(data, state, district, reference, days, mode):
    return data.assign(scope_state=state, scope_district=district,
        reference_date=str(reference), lookback_days=days, comparison_mode=mode,
        interpretation='Historical observed prices; excludes travel and stock availability')

def price_reach(latest):
    """Empirical cumulative share, one eligible observation per shop."""
    reach=latest.groupby('price').size().rename('shops').reset_index().sort_values('price')
    reach['cumulative_shops']=reach.shops.cumsum()
    reach['share']=reach.cumulative_shops/len(latest)*100
    return reach

def retailer_summary(latest):
    work=latest.assign(retailer=latest.premise_type.astype(str).str.strip().replace('', 'Unspecified'))
    return work.groupby('retailer').agg(low=('price','min'),lower=('price',lambda s:s.quantile(.25)),median=('price','median'),upper=('price',lambda s:s.quantile(.75)),high=('price','max'),shops=('price','size')).reset_index()

def shop_stability(history, minimum_days=3):
    result=history.groupby('premise_code',observed=True).agg(median=('price','median'),mean=('price','mean'),std=('price','std'),low=('price','min'),high=('price','max'),days=('date','nunique')).reset_index()
    result=result[result.days.ge(minimum_days)].copy()
    result['variation_pct']=result['std']/result['mean']*100
    return result

def basket_coverage_matrix(latest, quantities, shops, limit=20):
    counts=latest[latest.item_code.isin(quantities)].groupby('premise_code').item_code.nunique()
    eligible=shops[['premise_code','premise']].copy()
    eligible['observed_items']=eligible.premise_code.map(counts).fillna(0).astype(int)
    # Coverage ordering is deliberately independent of partial-basket prices.
    eligible=eligible.sort_values(['observed_items','premise_code'],ascending=[False,True]).head(limit)
    grid=eligible.merge(pd.DataFrame({'item_code':list(quantities)}),how='cross')
    grid=grid.merge(latest[['premise_code','item_code','price','date','age_days']],on=['premise_code','item_code'],how='left',validate='one_to_one')
    grid['status']=grid.price.notna().map({True:'Observed',False:'Missing'})
    grid['shop_label']=grid.premise.astype(str).str.slice(0,38)+' · #'+grid.premise_code.astype(str)
    grid['product_code']='#'+grid.item_code.astype(str)
    return grid
