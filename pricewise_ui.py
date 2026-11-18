import pandas as pd
import streamlit as st
from pricewise_core import latest_prices, maps_url
from pricewise_analytics import area, product_history, comparison_export

def context():
    return st.session_state['pw_data']

def heading(kicker, title, description):
    st.caption(kicker)
    st.title(title)
    st.caption(description)

def location(data, required=False):
    state, district = location_controls(required)
    return area(data, state, district), state, district

def location_controls(required=False):
    shops = context()[2].dropna(subset=['state','district'])
    states = sorted(s for s in shops.state.unique() if s)
    a, b = st.columns(2)
    state_key='state_' + str(required)
    district_key='district_' + str(required)
    options=states if required else ['All Malaysia']+states
    previous_state=st.session_state.get('location_state')
    state_index=options.index(previous_state) if previous_state in options else 0
    state=a.selectbox('State / federal territory',options,index=state_index,key=state_key)
    available=shops if state=='All Malaysia' else shops[shops.state.eq(state)]
    districts=['All districts']+sorted(d for d in available.district.unique() if d)
    previous_district=st.session_state.get('location_district') if previous_state==state else 'All districts'
    district_index=districts.index(previous_district) if previous_district in districts else 0
    if st.session_state.get(district_key) not in districts or previous_state!=state:
        st.session_state.pop(district_key,None)
    district=b.selectbox('District',districts,index=district_index,key=district_key)
    st.session_state['location_state']=state
    st.session_state['location_district']=district
    return state, district

def selected_history(data, code, state, district):
    return area(product_history(data, st.session_state['pw_signature'], int(code)), state, district)

def scope_note(state, district, reference=None, days=None):
    text = f':material/location_on: {state} / {district}'
    if reference is not None:
        text += f" · {pd.Timestamp(reference)-pd.Timedelta(days=days-1):%d %b}–{reference:%d %b %Y}"
    st.caption(text)

def product_labels(items):
    labels = items.set_index('item_code').apply(
        lambda row: f"{row['item']} · {row['unit']}", axis=1)
    duplicates = labels.duplicated(keep=False)
    for code in labels.index[duplicates]:
        labels.loc[code] += f" · #{code}"
    return labels.to_dict()

def reset_product_steps(key, steps):
    for step in steps:
        st.session_state.pop(f'{key}_{step}', None)

def product(items, key='atlas_product'):
    if items.empty:
        st.info('No comparable products are available in this dataset.')
        return None
    # Show a real analytical example on first visit; basket selection remains manual.
    if key != 'basket_product' and f'{key}_group' not in st.session_state:
        initial = items[items.item_code.eq(st.session_state.get('last_analytical_code', 1))]
        row = initial.iloc[0] if not initial.empty else items.iloc[0]
        for step, col in [('group','item_group'),('category','item_category'),('unit','unit'),('selection','item_code')]:
            st.session_state[f'{key}_{step}'] = row[col]
        st.session_state['analytical_product_initialized'] = True
    st.subheader('Choose a product')
    st.caption('Follow the steps to narrow the catalogue. Each choice updates the next step.')
    a, b = st.columns(2)
    group = a.selectbox('1. Product group', sorted(items.item_group.dropna().unique()),
        index=None, placeholder='Choose a group', key=f'{key}_group',
        on_change=reset_product_steps, args=(key, ['category', 'unit', 'selection']))
    grouped = items[items.item_group == group] if group is not None else items.iloc[:0]
    category = b.selectbox('2. Product category', sorted(grouped.item_category.dropna().unique()),
        index=None, placeholder='Choose a category', disabled=group is None, key=f'{key}_category',
        on_change=reset_product_steps, args=(key, ['unit', 'selection']))
    classified = grouped[grouped.item_category == category] if category is not None else grouped.iloc[:0]
    c, d = st.columns([1, 2])
    unit = c.selectbox('3. Pack size / unit', sorted(classified.unit.dropna().unique()),
        index=None, placeholder='Choose a pack size or unit', disabled=category is None, key=f'{key}_unit',
        on_change=reset_product_steps, args=(key, ['selection']))
    available = classified[classified.unit == unit].sort_values(['item', 'item_code']) if unit is not None else classified.iloc[:0]
    # Remove only a literal repeated category prefix; preserve brand and variant text.
    def short_name(row):
        name = str(row['item']).strip()
        prefix = str(category or '').strip()
        if prefix and name.casefold().startswith(prefix.casefold() + ' '):
            remainder = name[len(prefix):].lstrip(' -:')
            if remainder:
                name = remainder
        return name
    labels = {int(row['item_code']): short_name(row) for _, row in available.iterrows()}
    if labels:
        counts = pd.Series(labels).value_counts()
        labels = {code: label + (f' · #{code}' if counts[label] > 1 else '') for code, label in labels.items()}
    code = d.selectbox('4. Product / variant', available.item_code.tolist(), format_func=labels.get,
        index=None, placeholder='Choose or type to search variants', disabled=unit is None,
        key=f'{key}_selection')
    if code is None:
        st.info('Choose a group, category, pack size and product to view its prices.')
        return None
    if key != 'basket_product':
        st.session_state['last_analytical_code'] = int(code)
    row = available.set_index('item_code').loc[code]
    st.markdown(f"**Selected product:** {row['item']}")
    st.caption(f"{group} → {category} → {unit} · Item code: {code} · {len(available):,} variants in this selection")
    return code

def window(data):
    a, b = st.columns([1, 1.6])
    initial=st.session_state.get('saved_reference',data.date.max().date())
    initial=max(data.date.min().date(),min(initial,data.date.max().date()))
    reference = a.date_input('Reference date', initial, min_value=data.date.min().date(), max_value=data.date.max().date(),key='reference_date')
    if reference is None:
        st.info('Choose a reference date to compare observed prices.');st.stop()
    st.session_state['saved_reference']=reference
    modes=['7-day lookback', 'Exact date', 'Custom']
    mode = b.segmented_control('Price matching',modes,default=st.session_state.get('saved_matching','7-day lookback'),key='price_matching') or '7-day lookback'
    st.session_state['saved_matching']=mode
    if mode=='Custom':
        days=int(st.number_input('Calendar days',1,31,st.session_state.get('saved_lookback',7),key='custom_lookback'))
        st.session_state['saved_lookback']=days
    else:days=1 if mode=='Exact date' else 7
    st.caption(f'Latest eligible observation per product and outlet · {pd.Timestamp(reference) - pd.Timedelta(days=days-1):%d %b}–{reference:%d %b %Y} · No future observations')
    return reference, days

def metrics(values):
    with st.container(horizontal=True):
        for label, value in values:
            st.metric(label, value, border=True)

def table(data, name='Observed prices'):
    display = data.copy()
    if display.empty:
        st.info('No matching records. Clear the search or broaden your filters.')
        return display
    if {'premise','address','district','state'}.issubset(display.columns):
        display['Directions'] = display.apply(maps_url, axis=1)
    display = display.rename(columns={'price': 'Price (RM)', 'date': 'Observed on', 'age_days': 'Age (days)', 'line_total': 'Item total (RM)', 'total': 'Basket total (RM)', 'item': 'Product', 'unit': 'Unit', 'premise': 'Shop', 'address': 'Address', 'quantity': 'Quantity', 'district': 'District', 'state': 'State', 'premise_type': 'Retailer type'})
    st.dataframe(display, hide_index=True, width='stretch', column_config={'Observed on': st.column_config.DateColumn(format='DD MMM YYYY'), 'Directions': st.column_config.LinkColumn('Directions', display_text='Open map'), **{col: st.column_config.NumberColumn(col, format='RM %.2f') for col in ['Price (RM)', 'Item total (RM)', 'Basket total (RM)']}})
    return display

def export(data, filename, state, district, reference, days):
    output = comparison_export(data, state, district, reference, days, filename.removesuffix('.csv'))
    st.download_button('Export this comparison', output.to_csv(index=False).encode('utf-8-sig'), filename, 'text/csv', icon=':material/download:')

DETAILS = ['item', 'unit', 'quantity', 'price', 'line_total', 'date', 'age_days', 'premise', 'address', 'premise_type', 'state', 'district']


def product_empty():
    st.caption('Complete the product selection above to explore comparable prices.')

def shop_labels(frame):
    frame = frame.copy()
    frame['shop_label'] = frame['premise'].astype(str).str.slice(0,42) + ' · #' + frame.premise_code.astype(str)
    return frame

def footer():
    st.caption('PRICEWISE MALAYSIA · PriceCatcher historical observations · Prices are per listed unit. No stock or travel-cost information is implied.')


def selection_summary(items, code):
    row=items.set_index('item_code').loc[code]
    st.markdown(f":green-badge[{row['unit']}] **{row['item']}**")
    st.caption(f"{row['item_group']} / {row['item_category']} · Item #{code}")
